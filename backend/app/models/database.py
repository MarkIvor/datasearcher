from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, create_engine, JSON
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), default="")
    role = Column(String(20), default="analyst")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, default="")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(Integer, primary_key=True)
    llm_url = Column(String(500), default="")
    llm_api_key = Column(String(500), default="")
    llm_model = Column(String(200), default="")
    can_use_custom_llm = Column(Boolean, default=True)
    can_use_db_connections = Column(Boolean, default=True)


class DBConnection(Base):
    __tablename__ = "db_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    db_type = Column(String(30), nullable=False)
    connection_string = Column(Text, nullable=False)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(12), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    password_hash = Column(String(255), nullable=True)
    config = Column(JSON, nullable=False)
    snapshot_dir = Column(String(500), nullable=False)
    tables_info = Column(JSON, default=[])
    created_by = Column(Integer, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


DATABASE_URL = "sqlite:///datasearcher.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        defaults = {
            "allow_registration": "true",
            "allow_custom_llm": "true",
            "allow_user_db_connections": "true",
            "global_llm_url": "",
            "global_llm_model": "",
            "global_llm_api_key": "",
        }
        for k, v in defaults.items():
            exists = db.query(AppSettings).filter(AppSettings.key == k).first()
            if not exists:
                db.add(AppSettings(key=k, value=v))
        admin_exists = db.query(User).filter(User.role == "admin").first()
        if not admin_exists:
            from passlib.context import CryptContext as _CC
            pwd_ctx = _CC(schemes=["bcrypt"], deprecated="auto")
            admin_email = os.environ.get("ADMIN_EMAIL", "admin@datasearcher.com")
            admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
            admin = User(
                email=admin_email,
                password_hash=pwd_ctx.hash(admin_password),
                display_name="Admin",
                role="admin",
                is_active=True,
            )
            db.add(admin)
        db.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
