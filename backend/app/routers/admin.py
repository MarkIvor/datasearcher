from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models.database import get_db, User, AppSettings, UserSettings, DBConnection
from ..services.auth_service import get_app_setting, set_app_setting, hash_password
from .auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    display_name: str | None = None
    password: str | None = None
    can_use_custom_llm: bool | None = None
    can_use_db_connections: bool | None = None


class UserLLMRequest(BaseModel):
    llm_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""


class SettingsUpdate(BaseModel):
    settings: dict


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Требуется роль администратора")
    return user


@router.get("/users")
async def list_users(admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    result = []
    for u in users:
        us = db.query(UserSettings).filter(UserSettings.user_id == u.id).first()
        result.append({
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "role": u.role,
            "is_active": u.is_active,
            "can_use_custom_llm": us.can_use_custom_llm if us else True,
            "can_use_db_connections": us.can_use_db_connections if us else True,
            "has_custom_llm": bool(us and (us.llm_url or us.llm_model or us.llm_api_key)),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return result


@router.put("/users/{user_id}")
async def update_user(user_id: int, body: UpdateUserRequest, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if user_id == admin.id and body.role and body.role != "admin":
        raise HTTPException(400, "Нельзя снять роль админа у себя")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.password:
        user.password_hash = hash_password(body.password)

    if body.can_use_custom_llm is not None or body.can_use_db_connections is not None:
        us = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not us:
            us = UserSettings(user_id=user_id)
            db.add(us)
        if body.can_use_custom_llm is not None:
            us.can_use_custom_llm = body.can_use_custom_llm
        if body.can_use_db_connections is not None:
            us.can_use_db_connections = body.can_use_db_connections

    db.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(400, "Нельзя удалить себя")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.get("/settings")
async def get_settings(admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    rows = db.query(AppSettings).all()
    return {r.key: r.value for r in rows}


@router.put("/settings")
async def update_settings(body: SettingsUpdate, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    for k, v in body.settings.items():
        set_app_setting(db, k, str(v))
    return {"ok": True}


@router.get("/users/{user_id}/llm")
async def get_user_llm(user_id: int, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    us = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not us:
        return {"llm_url": "", "llm_model": "", "llm_api_key": ""}
    return {"llm_url": us.llm_url or "", "llm_model": us.llm_model or "", "llm_api_key": us.llm_api_key or ""}


@router.put("/users/{user_id}/llm")
async def set_user_llm(user_id: int, body: UserLLMRequest, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    us = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not us:
        us = UserSettings(user_id=user_id)
        db.add(us)
    us.llm_url = body.llm_url
    us.llm_model = body.llm_model
    us.llm_api_key = body.llm_api_key
    db.commit()
    return {"ok": True}


@router.get("/users/{user_id}/connections")
async def get_user_connections(user_id: int, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    conns = db.query(DBConnection).filter(DBConnection.user_id == user_id).all()
    return [
        {"id": c.id, "name": c.name, "db_type": c.db_type, "is_public": c.is_public}
        for c in conns
    ]


class AdminCreateConnection(BaseModel):
    name: str
    db_type: str = "postgresql"
    host: str = ""
    port: int = 5432
    database: str = ""
    username: str = ""
    password: str = ""
    is_public: bool = False


@router.post("/users/{user_id}/connections")
async def create_user_connection(user_id: int, body: AdminCreateConnection, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    from ..services.auth_service import encrypt_connection_string
    if body.db_type == "sqlite":
        conn_str = f"sqlite:///{body.database}"
    elif body.db_type == "postgresql":
        conn_str = f"postgresql://{body.username}:{body.password}@{body.host}:{body.port}/{body.database}"
    elif body.db_type == "mysql":
        conn_str = f"mysql+pymysql://{body.username}:{body.password}@{body.host}:{body.port}/{body.database}"
    elif body.db_type == "clickhouse":
        conn_str = f"clickhouse://{body.username}:{body.password}@{body.host}:{body.port}/{body.database}"
    else:
        raise HTTPException(400, f"Неподдерживаемый тип БД: {body.db_type}")
    encrypted = encrypt_connection_string(conn_str)
    conn = DBConnection(
        user_id=user_id, name=body.name, db_type=body.db_type,
        connection_string=encrypted, is_public=body.is_public,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {"id": conn.id, "name": conn.name, "db_type": conn.db_type}


@router.delete("/users/{user_id}/connections/{conn_id}")
async def delete_user_connection(user_id: int, conn_id: int, admin: User = Depends(_require_admin), db: Session = Depends(get_db)):
    conn = db.query(DBConnection).filter(DBConnection.id == conn_id, DBConnection.user_id == user_id).first()
    if not conn:
        raise HTTPException(404, "Подключение не найдено")
    db.delete(conn)
    db.commit()
    return {"ok": True}
