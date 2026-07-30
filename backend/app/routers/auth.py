from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..models.database import get_db, User
from ..services.auth_service import (
    register_user, authenticate_user,
    create_access_token, create_refresh_token, decode_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    user: dict


def _get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(401, "Не авторизован")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(401, "Токен недействителен")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(401, "Пользователь не найден")
    return user


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return _get_current_user(request, db)


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    try:
        return _get_current_user(request, db)
    except HTTPException:
        return None


@router.post("/register")
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if len(body.password) < 6:
        raise HTTPException(400, "Пароль минимум 6 символов")

    result = register_user(db, body.email, body.password, body.display_name)
    if isinstance(result, str):
        raise HTTPException(400, result)

    user = result
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)

    resp_data = {
        "access_token": access,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
    }
    resp = Response(content=__import__("json").dumps(resp_data, ensure_ascii=False), media_type="application/json")
    resp.set_cookie("access_token", access, httponly=True, max_age=1800, samesite="lax")
    resp.set_cookie("refresh_token", refresh, httponly=True, max_age=604800, samesite="lax")
    return resp


@router.post("/login")
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(401, "Неверный email или пароль")

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)

    resp_data = {
        "access_token": access,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
    }
    resp = Response(content=__import__("json").dumps(resp_data, ensure_ascii=False), media_type="application/json")
    resp.set_cookie("access_token", access, httponly=True, max_age=1800, samesite="lax")
    resp.set_cookie("refresh_token", refresh, httponly=True, max_age=604800, samesite="lax")
    return resp


@router.post("/refresh")
async def refresh(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Нет refresh-токена")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Недействительный refresh-токен")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(401, "Пользователь не найден")

    access = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    resp_data = {
        "access_token": access,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role},
    }
    resp = Response(content=__import__("json").dumps(resp_data, ensure_ascii=False), media_type="application/json")
    resp.set_cookie("access_token", access, httponly=True, max_age=1800, samesite="lax")
    resp.set_cookie("refresh_token", refresh_token, httponly=True, max_age=604800, samesite="lax")
    return resp


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


@router.post("/logout")
async def logout():
    resp = Response(content='{"ok":true}', media_type="application/json")
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    return resp
