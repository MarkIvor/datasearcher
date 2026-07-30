from __future__ import annotations

from fastapi import APIRouter, Depends

from .auth import get_current_user
from ..models.database import User

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/query")
async def query_logs(limit: int = 50, user: User = Depends(get_current_user)):
    from ..services.logging_db import get_log_db
    return get_log_db().get_query_logs(limit=limit)


@router.get("/error")
async def error_logs(limit: int = 50, user: User = Depends(get_current_user)):
    from ..services.logging_db import get_log_db
    return get_log_db().get_error_logs(limit=limit)


@router.get("/audit")
async def audit_logs(limit: int = 50, user: User = Depends(get_current_user)):
    from ..services.logging_db import get_log_db
    return get_log_db().get_audit_logs(limit=limit)