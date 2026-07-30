from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="sync_datahub",
    description="Синхронизация метаданных из DataHub (описания датасетов, колонки, владельцы, глоссарий) в Knowledge Base. Требует настройки DATAHUB_URL.",
    parameters={
        "type": "object",
        "properties": {},
    },
)
def sync_datahub(session: Session) -> str:
    from ..datahub_client import DataHubClient

    client = DataHubClient()
    if not client.enabled:
        return "❌ DataHub не настроен. Задайте DATAHUB_URL в настройках."

    result = client.sync_datasets()
    if "error" in result:
        return f"❌ {result['error']}"

    return f"✅ Синхронизировано датасетов из DataHub: {result.get('synced', 0)}."