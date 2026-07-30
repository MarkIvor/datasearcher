from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="add_example",
    description="Добавить эталонную пару «запрос на русском → SQL» в Example Store для few-shot обучения. Используй для накопления примеров, улучшающих generate_sql.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Вопрос на естественном языке"},
            "sql": {"type": "string", "description": "Эталонный SQL"},
            "table_name": {"type": "string", "description": "Имя таблицы (необязательно)"},
            "is_golden": {"type": "boolean", "description": "Золотой пример (высокий приоритет)"},
        },
        "required": ["query", "sql"],
    },
)
def add_example(
    session: Session,
    query: str,
    sql: str,
    table_name: str = "",
    is_golden: bool = False,
) -> str:
    from ..example_store import get_example_store
    store = get_example_store()
    if store is None:
        return "Example Store отключён (example_store_enabled=false)."
    ex_id = store.add_example(query, sql, table_name, success=True, is_golden=is_golden)
    star = " ⭐ golden" if is_golden else ""
    return f"✅ Пример #{ex_id} добавлен в Example Store{star}."