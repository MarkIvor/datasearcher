from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models.database import get_db, User
from ..services.auth_service import get_app_setting, set_app_setting, get_user_llm_settings, set_user_llm_settings
from .auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMSettings(BaseModel):
    llm_base_url: str
    llm_api_key: str
    llm_model: str


class LLMSettingsResponse(BaseModel):
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_connected: bool = False


@router.get("/", response_model=LLMSettingsResponse)
async def get_settings(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    llm = get_user_llm_settings(db, user.id)
    api_key = llm["llm_api_key"]
    masked = api_key[:8] + "..." if len(api_key) > 8 else api_key

    connected = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = await client.get(f"{llm['llm_url']}/models", headers=headers)
            if resp.status_code == 200:
                connected = True
    except Exception:
        pass

    return LLMSettingsResponse(
        llm_base_url=llm["llm_url"],
        llm_api_key=masked,
        llm_model=llm["llm_model"],
        llm_connected=connected,
    )


@router.put("/")
async def update_settings(request: Request, body: LLMSettings, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base_url = body.llm_base_url.rstrip("/")
    api_key = body.llm_api_key
    model = body.llm_model

    if api_key.endswith("..."):
        existing = get_user_llm_settings(db, user.id)
        api_key = existing["llm_api_key"]

    if user.role == "admin":
        set_app_setting(db, "global_llm_url", base_url)
        set_app_setting(db, "global_llm_api_key", api_key)
        set_app_setting(db, "global_llm_model", model)

    set_user_llm_settings(db, user.id, base_url, model, api_key)

    app_llm = request.app.state.llm_service
    if user.role == "admin":
        app_llm.base_url = base_url
        app_llm.api_key = api_key
        app_llm.model = model

    connected = False
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = await client.get(f"{base_url}/models", headers=headers)
            if resp.status_code == 200:
                connected = True
    except Exception:
        pass

    return {"ok": True, "connected": connected}


@router.post("/test")
async def test_connection(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    llm = get_user_llm_settings(db, user.id)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            headers = {"Content-Type": "application/json"}
            if llm["llm_api_key"]:
                headers["Authorization"] = f"Bearer {llm['llm_api_key']}"
            url = f"{llm['llm_url']}/models"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                model_ids = [m.get("id", "") for m in models]
                return {"connected": True, "models": model_ids}
            return {"connected": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}
