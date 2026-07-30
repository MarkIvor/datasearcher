from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .auth import get_current_user
from ..models.database import User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class UpdateTableMetaRequest(BaseModel):
    table_name: str
    connection: str = ""
    description: str | None = None
    owner: str | None = None
    layer: str | None = None
    tags: list[str] | None = None
    is_certified: bool | None = None


class UpdateColumnMetaRequest(BaseModel):
    table_name: str
    column_name: str
    description: str | None = None
    unit: str | None = None
    pii_type: str | None = None
    is_sensitive: bool | None = None


class UpsertMetricRequest(BaseModel):
    name: str
    formula: str = ""
    description: str = ""
    owner: str = ""


@router.get("/tables")
async def list_kb_tables(user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    return get_kb().all_tables()


@router.get("/tables/{table_name}")
async def get_kb_table(table_name: str, user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    kb = get_kb()
    table = kb.get_table(table_name)
    columns = kb.get_columns(table_name)
    return {"table": table, "columns": columns}


@router.put("/tables")
async def update_table_meta(body: UpdateTableMetaRequest, user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    from ..services.logging_db import get_log_db
    get_kb().upsert_table(
        table_name=body.table_name,
        connection=body.connection,
        description=body.description,
        owner=body.owner,
        layer=body.layer,
        tags=body.tags,
        is_certified=body.is_certified,
        source="manual",
    )
    get_log_db().log_audit(
        action="update_metadata", target=body.table_name,
        details={"owner": body.owner, "layer": body.layer},
    )
    return {"ok": True}


@router.put("/columns")
async def update_column_meta(body: UpdateColumnMetaRequest, user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    get_kb().upsert_column(
        table_name=body.table_name,
        column_name=body.column_name,
        description=body.description,
        unit=body.unit,
        pii_type=body.pii_type,
        is_sensitive=body.is_sensitive,
        source="manual",
    )
    return {"ok": True}


@router.get("/metrics")
async def list_metrics(user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    return get_kb().all_metrics()


@router.post("/metrics")
async def upsert_metric(body: UpsertMetricRequest, user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    get_kb().upsert_metric(body.name, body.formula, body.description, body.owner)
    return {"ok": True}


@router.delete("/metrics/{name}")
async def delete_metric(name: str, user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    ok = get_kb().delete_metric(name)
    if not ok:
        raise HTTPException(404, "Метрика не найдена")
    return {"ok": True}


@router.get("/search")
async def search_knowledge(q: str = "", limit: int = 10, user: User = Depends(get_current_user)):
    from ..services.knowledge_base import get_kb
    if not q:
        return []
    return get_kb().search(q, limit=limit)


@router.get("/examples")
async def list_examples(limit: int = 50, user: User = Depends(get_current_user)):
    from ..services.example_store import get_example_store
    store = get_example_store()
    if store is None:
        return []
    return store.all_examples(limit=limit)