from __future__ import annotations

import json

from app.session import Session
from .registry import register_tool


@register_tool(
    name="update_metadata",
    description="Обновить бизнес-описание таблицы и колонок в Knowledge Base (владелец, слой, описание, сертификация). Используй для обогащения анализа контекстом.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "description": {"type": "string", "description": "Бизнес-описание таблицы"},
            "owner": {"type": "string", "description": "Владелец данных"},
            "layer": {"type": "string", "description": "Слой: raw | staging | intermediate | mart"},
            "is_certified": {"type": "boolean", "description": "Сертифицированная таблица"},
            "column_descriptions": {
                "type": "string",
                "description": "JSON: {\"колонка\": \"описание\"}",
            },
        },
        "required": ["table_name"],
    },
)
def update_metadata(
    session: Session,
    table_name: str,
    description: str = "",
    owner: str = "",
    layer: str = "",
    is_certified: bool = False,
    column_descriptions: str = "",
) -> str:
    from ..knowledge_base import get_kb
    from ..logging_db import get_log_db

    kb = get_kb()
    kb.upsert_table(
        table_name=table_name,
        description=description or None,
        owner=owner or None,
        layer=layer or None,
        is_certified=is_certified if is_certified else None,
        source="manual",
    )

    cols_updated = 0
    if column_descriptions:
        try:
            cols = json.loads(column_descriptions)
            for col_name, col_desc in cols.items():
                kb.upsert_column(table_name, col_name, description=col_desc, source="manual")
                cols_updated += 1
        except json.JSONDecodeError:
            pass

    get_log_db().log_audit(
        action="update_metadata",
        target=table_name,
        details={"owner": owner, "layer": layer, "cols_updated": cols_updated},
    )

    out = [f"✅ Метаданные таблицы '{table_name}' обновлены."]
    if cols_updated:
        out.append(f"Обновлено описаний колонок: {cols_updated}")
    return "\n".join(out)