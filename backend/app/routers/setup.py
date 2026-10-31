from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings as cfg
from ..models.database import get_db, User, DBConnection
from ..services.auth_service import (
    decrypt_connection_string,
    get_app_setting,
    get_user_llm_settings,
    set_app_setting,
    set_user_llm_settings,
)
from .auth import get_current_user
from .connections import _conn_str_to_params

router = APIRouter(prefix="/api/setup", tags=["setup"])

VALID_MODES = {"interface", "mcp"}
STEPS_TOTAL = 4


class SetupUpdate(BaseModel):
    step: Optional[int] = None
    mode: Optional[str] = None
    scope: Optional[str] = None
    llm_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    completed: Optional[bool] = None


class TestLLMRequest(BaseModel):
    url: str = ""
    key: str = ""


class McpConfigRequest(BaseModel):
    connection_ids: list[int] = []


def _user_key(user_id: int, suffix: str) -> str:
    return f"setup_user_{user_id}_{suffix}"


def _mask_key(key: str) -> str:
    if not key:
        return ""
    return key[:8] + "..." if len(key) > 8 else key


def _setup_state(db: Session, user: User) -> dict:
    user_mode = get_app_setting(db, _user_key(user.id, "mode"))
    user_completed = get_app_setting(db, _user_key(user.id, "completed")) == "true"
    user_step = get_app_setting(db, _user_key(user.id, "step"))

    global_mode = get_app_setting(db, "setup_mode")
    global_completed = get_app_setting(db, "setup_completed") == "true"
    global_step = get_app_setting(db, "setup_step")

    llm = get_user_llm_settings(db, user.id)

    enterprise = {
        "read_only": cfg.read_only,
        "pii_masking": cfg.pii_masking,
        "rate_limit_enabled": cfg.rate_limit_enabled,
        "log_enabled": cfg.log_enabled,
        "default_mode": cfg.default_mode or "auto",
        "auto_translate": cfg.auto_translate,
    }

    conns_count = db.query(DBConnection).filter(
        (DBConnection.user_id == user.id) | (DBConnection.is_public == True)  # noqa: E712
    ).count()

    return {
        "completed": user_completed or global_completed,
        "mode": user_mode or global_mode or "",
        "step": int(user_step or global_step or 1),
        "steps_total": STEPS_TOTAL,
        "scope": "user" if user_mode else ("global" if global_mode else None),
        "is_admin": user.role == "admin",
        "llm": {
            "url": llm.get("llm_url", ""),
            "model": llm.get("llm_model", ""),
            "api_key_masked": _mask_key(llm.get("llm_api_key", "")),
            "has_key": bool(llm.get("llm_api_key")),
        },
        "enterprise": enterprise,
        "connections_count": conns_count,
    }


def _yaml_quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _connection_yaml_block(conn: DBConnection) -> str:
    conn_str = decrypt_connection_string(conn.connection_string)
    params = _conn_str_to_params(conn.db_type, conn_str)
    db_type = "postgresql" if conn.db_type == "postgresql" else conn.db_type
    mode = "auto"
    lines = [f"  - name: {_yaml_quote(conn.name)}", f"    db_type: {db_type}"]
    if conn.db_type == "api":
        lines.append(f"    base_url: {_yaml_quote(params.get('host', ''))}")
    else:
        lines.append(f"    host: {_yaml_quote(params.get('host', 'localhost'))}")
        if params.get("port"):
            lines.append(f"    port: {params['port']}")
        if params.get("database"):
            lines.append(f"    database: {_yaml_quote(params['database'])}")
        lines.append(f"    username: {_yaml_quote(params.get('username', ''))}")
        lines.append(f"    password: {_yaml_quote(params.get('password', ''))}")
    lines.append(f"    mode: {mode}")
    return "\n".join(lines)


@router.get("/")
async def get_setup(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _setup_state(db, user)


@router.put("/")
async def update_setup(
    body: SetupUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.mode is not None and body.mode not in VALID_MODES:
        raise HTTPException(400, f"Недопустимый тип: {body.mode}. Доступны: interface, mcp")

    scope = body.scope or get_app_setting(db, _user_key(user.id, "scope")) or "user"
    if scope == "global" and user.role != "admin":
        scope = "user"

    if body.step is not None:
        if not 1 <= body.step <= STEPS_TOTAL:
            raise HTTPException(400, f"Шаг должен быть 1..{STEPS_TOTAL}")
        set_app_setting(db, _user_key(user.id, "step"), str(body.step))
        if scope == "global":
            set_app_setting(db, "setup_step", str(body.step))

    if body.mode is not None:
        set_app_setting(db, _user_key(user.id, "mode"), body.mode)
        if scope == "global":
            set_app_setting(db, "setup_mode", body.mode)

    set_app_setting(db, _user_key(user.id, "scope"), scope)

    api_key = body.llm_api_key
    if api_key and api_key.endswith("..."):
        existing = get_user_llm_settings(db, user.id)
        api_key = existing["llm_api_key"]
    if api_key is None:
        api_key = ""

    if body.llm_url is not None or body.llm_model is not None or api_key:
        existing = get_user_llm_settings(db, user.id)
        url = (body.llm_url or existing["llm_url"]).rstrip("/")
        model = body.llm_model or existing["llm_model"]
        key = api_key or existing["llm_api_key"]
        set_user_llm_settings(db, user.id, url, model, key)
        if scope == "global" and user.role == "admin":
            set_app_setting(db, "global_llm_url", url)
            set_app_setting(db, "global_llm_model", model)
            set_app_setting(db, "global_llm_api_key", key)
        svc = getattr(request.app.state, "llm_service", None)
        if svc is not None and user.role == "admin":
            svc.base_url = url
            svc.api_key = key
            svc.model = model

    if body.completed is not None:
        set_app_setting(db, _user_key(user.id, "completed"), "true" if body.completed else "false")
        if scope == "global" and user.role == "admin":
            set_app_setting(db, "setup_completed", "true" if body.completed else "false")

    return _setup_state(db, user)


@router.post("/test-llm")
async def test_llm(
    body: TestLLMRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = get_user_llm_settings(db, user.id)
    url = (body.url or existing["llm_url"]).rstrip("/")
    key = body.key
    if key.endswith("..."):
        key = existing["llm_api_key"]
    if not key:
        key = existing["llm_api_key"]
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"
            resp = await client.get(f"{url}/models", headers=headers)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                return {"connected": True, "models": [m.get("id", "") for m in models]}
            return {"connected": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@router.post("/mcp-config")
async def generate_mcp_config(
    body: McpConfigRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(DBConnection).filter(
        (DBConnection.user_id == user.id) | (DBConnection.is_public == True)  # noqa: E712
    )
    if body.connection_ids:
        query = query.filter(DBConnection.id.in_(body.connection_ids))
    conns = query.all()

    if not conns:
        raise HTTPException(400, "Нет подключений к БД — добавьте их на шаге «Данные» или во вкладке «БД»")

    blocks = [_connection_yaml_block(c) for c in conns]
    connections_yaml = "connections:\n" + "\n".join(blocks) + "\n"

    llm = get_user_llm_settings(db, user.id)
    env_lines = []
    if llm.get("llm_url"):
        env_lines.append(f"LLM_BASE_URL={llm['llm_url']}")
        env_lines.append(f"LLM_MODEL={llm.get('llm_model', '')}")
        if llm.get("llm_api_key"):
            env_lines.append(f"LLM_API_KEY={llm['llm_api_key']}")
    env_block = "\n".join(env_lines)

    server_entry = {
        "command": "datasearcher-mcp",
        "args": ["--config", "/path/to/connections.yaml"],
    }
    client_json = json.dumps({"mcpServers": {"datasearcher": server_entry}}, indent=2)

    http_command = (
        "datasearcher-mcp --transport http --host 0.0.0.0 --port 8000 --auth-token secret123"
    )
    docker_command = (
        "cd mcp && docker compose -f docker-compose.yml up -d   # http://localhost:8100/mcp"
    )

    return {
        "connections_yaml": connections_yaml,
        "claude_json": client_json,
        "cursor_json": client_json,
        "http_command": http_command,
        "docker_command": docker_command,
        "env_block": env_block,
        "connections": [c.name for c in conns],
    }
