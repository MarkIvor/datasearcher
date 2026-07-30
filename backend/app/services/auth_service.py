from __future__ import annotations

import os
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..models.database import User, AppSettings, UserSettings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    import sys
    print("WARNING: JWT_SECRET not set! Using random secret. Set JWT_SECRET env var for production.")
    JWT_SECRET = os.urandom(32).hex()

JWT_ALGO = "HS256"
ACCESS_TTL = timedelta(minutes=30)
REFRESH_TTL = timedelta(days=7)

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_ctx.verify(password, hashed)


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": datetime.utcnow() + ACCESS_TTL,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def create_refresh_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + REFRESH_TTL,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def register_user(db: Session, email: str, password: str, display_name: str = "") -> User | str:
    allow = get_app_setting(db, "allow_registration")
    if allow != "true":
        return "Регистрация отключена администратором"

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return "Пользователь с таким email уже существует"

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name or email.split("@")[0],
        role="analyst",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_app_setting(db: Session, key: str) -> str:
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    return row.value if row else ""


def set_app_setting(db: Session, key: str, value: str):
    row = db.query(AppSettings).filter(AppSettings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSettings(key=key, value=value))
    db.commit()


def get_user_llm_settings(db: Session, user_id: int) -> dict:
    from ..config import settings as _s
    allow_custom = get_app_setting(db, "allow_custom_llm") == "true"
    global_url = get_app_setting(db, "global_llm_url") or _s.llm_base_url
    global_model = get_app_setting(db, "global_llm_model") or _s.llm_model
    global_key = get_app_setting(db, "global_llm_api_key") or _s.llm_api_key

    result = {"llm_url": global_url, "llm_model": global_model, "llm_api_key": global_key}

    us = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    if allow_custom and us and us.can_use_custom_llm:
        if us.llm_url:
            result["llm_url"] = us.llm_url
        if us.llm_model:
            result["llm_model"] = us.llm_model
        if us.llm_api_key:
            result["llm_api_key"] = us.llm_api_key

    return result


def set_user_llm_settings(db: Session, user_id: int, llm_url: str, llm_model: str, llm_api_key: str):
    allow_custom = get_app_setting(db, "allow_custom_llm")
    if allow_custom != "true":
        return False

    us = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if us:
        us.llm_url = llm_url
        us.llm_model = llm_model
        us.llm_api_key = llm_api_key
    else:
        db.add(UserSettings(user_id=user_id, llm_url=llm_url, llm_model=llm_model, llm_api_key=llm_api_key))
    db.commit()
    return True


def encrypt_connection_string(conn_str: str) -> str:
    if not ENCRYPTION_KEY:
        return conn_str
    from cryptography.fernet import Fernet
    key = _derive_fernet_key(ENCRYPTION_KEY)
    return Fernet(key).encrypt(conn_str.encode()).decode()


def decrypt_connection_string(encrypted: str) -> str:
    if not ENCRYPTION_KEY:
        return encrypted
    from cryptography.fernet import Fernet
    key = _derive_fernet_key(ENCRYPTION_KEY)
    return Fernet(key).decrypt(encrypted.encode()).decode()


def _derive_fernet_key(raw_key: str) -> bytes:
    import hashlib, base64
    derived = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(derived)
