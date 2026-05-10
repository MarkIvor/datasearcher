from __future__ import annotations

import json

from app.session import Session
from .registry import register_tool


@register_tool(
    name="classify_rows",
    description="Классификация строк таблицы по категориям с помощью LLM. Полезно для сегментации, определения тональности, категоризации текстов и т.д. LLM получает батч строк и возвращает категорию для каждой.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Имя таблицы",
            },
            "columns": {
                "type": "string",
                "description": "Колонки для классификации через запятую",
            },
            "categories": {
                "type": "string",
                "description": "Категории через запятую (например: позитивный,негативный,нейтральный)",
            },
            "instruction": {
                "type": "string",
                "description": "Дополнительная инструкция по классификации",
            },
            "where": {
                "type": "string",
                "description": "SQL WHERE условие для фильтрации строк (необязательно)",
            },
            "limit": {
                "type": "integer",
                "description": "Максимальное количество строк для классификации (по умолчанию 200)",
            },
        },
        "required": ["table_name", "columns", "categories"],
    },
)
def classify_rows(
    session: Session,
    table_name: str,
    columns: str,
    categories: str,
    instruction: str = "",
    where: str = "",
    limit: int = 200,
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    cols = [c.strip() for c in columns.split(",")]
    cats = [c.strip() for c in categories.split(",")]

    select_cols = ", ".join(f'"{c}"' for c in cols)
    sql = f'SELECT rowid, {select_cols} FROM "{table_name}"'
    if where.strip():
        sql += f" WHERE {where}"
    sql += f" LIMIT {min(limit, 500)}"

    try:
        rows = conn.execute(sql).fetchall()
    except Exception as e:
        return f"SQL ошибка: {e}"

    if not rows:
        return "Нет строк для классификации."

    row_ids = [r[0] for r in rows]
    data_rows = [r[1:] for r in rows]

    return (
        f"__CLASSIFY_TASK__\n"
        f"columns={json.dumps(cols)}\n"
        f"categories={json.dumps(cats)}\n"
        f"instruction={instruction}\n"
        f"table_name={table_name}\n"
        f"row_ids={json.dumps(row_ids)}\n"
        f"data={json.dumps(data_rows, ensure_ascii=False, default=str)}\n"
        f"__END_CLASSIFY_TASK__"
    )
