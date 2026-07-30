from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel

from .auth import get_current_user
from ..models.database import User

router = APIRouter(prefix="/api/metadata", tags=["metadata"])


@router.post("/dbt")
async def load_dbt_manifest(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    from ..services.dbt_loader import load_dbt_manifest

    content = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="wb")
    tmp.write(content)
    tmp.close()
    try:
        result = load_dbt_manifest(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/dbt/semantic")
async def load_dbt_semantic(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    from ..services.dbt_loader import load_dbt_semantic_models

    content = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yml", mode="wb")
    tmp.write(content)
    tmp.close()
    try:
        result = load_dbt_semantic_models(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


class DataHubSyncRequest(BaseModel):
    limit: int = 100


class BILinkRequest(BaseModel):
    tool: str
    base_url: str
    dashboard_id: str = ""
    params: dict | None = None
    time_from: str = ""
    time_to: str = ""


@router.post("/bi-link")
async def build_bi_link(body: BILinkRequest, user: User = Depends(get_current_user)):
    from ..services.bi_linker import build_bi_link as _build
    time_range = None
    if body.time_from and body.time_to:
        time_range = (body.time_from, body.time_to)
    url = _build(
        tool=body.tool, base_url=body.base_url, dashboard_id=body.dashboard_id,
        params=body.params or {}, time_range=time_range,
    )
    return {"url": url}


@router.post("/datahub/sync")
async def sync_datahub(body: DataHubSyncRequest, user: User = Depends(get_current_user)):
    from ..services.datahub_client import DataHubClient
    client = DataHubClient()
    if not client.enabled:
        raise HTTPException(400, "DataHub не настроен. Задайте DATAHUB_URL.")
    return client.sync_datasets(limit=body.limit)


@router.get("/datahub/lineage/{urn}")
async def datahub_lineage(urn: str, user: User = Depends(get_current_user)):
    from ..services.datahub_client import DataHubClient
    client = DataHubClient()
    if not client.enabled:
        raise HTTPException(400, "DataHub не настроен.")
    return client.get_lineage(urn)


@router.post("/pii/scan/{table_name}")
async def scan_table_pii(table_name: str, request: Request, user: User = Depends(get_current_user)):
    from ..services.pii_detector import scan_table_for_pii
    mgr = request.app.state.session_manager
    session_id = request.cookies.get("session_id")
    session = mgr.get_or_create(session_id)
    try:
        desc = session.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
        col_info = [{"name": r[0], "type": r[1]} for r in desc]
        from ..config import settings
        rows = session.conn.execute(
            f'SELECT * FROM "{table_name}" LIMIT {settings.pii_scan_rows}'
        ).fetchall()
    except Exception as e:
        raise HTTPException(400, f"Ошибка: {e}")
    return scan_table_for_pii(table_name, col_info, rows)