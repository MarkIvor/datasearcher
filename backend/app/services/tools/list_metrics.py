from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="list_metrics",
    description="Показать список расчётных метрик из Knowledge Base (имя, формула, описание, владелец). Используй чтобы узнать как считаются бизнес-метрики.",
    parameters={
        "type": "object",
        "properties": {},
    },
)
def list_metrics(session: Session) -> str:
    from ..knowledge_base import get_kb
    kb = get_kb()
    metrics = kb.all_metrics()
    if not metrics:
        return "В Knowledge Base нет сохранённых метрик. Добавьте через update_metadata или load_dbt."

    rows = [
        (m.get("name", ""), (m.get("formula") or "")[:50], (m.get("description") or "")[:50])
        for m in metrics
    ]
    return f"Метрики ({len(rows)}):\n\n" + format_table(["name", "formula", "description"], rows)