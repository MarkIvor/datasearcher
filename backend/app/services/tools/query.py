from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="sql_query",
    description="Выполняет SQL-запрос к загруженным таблицам. Можно использовать JOIN между таблицами, агрегации, оконные функции и весь синтаксис DuckDB. Имена таблиц соответствуют именам загруженных файлов.",
    parameters={
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Валидный SQL запрос (DuckDB синтаксис). Имена таблиц из списка загруженных файлов.",
            }
        },
        "required": ["sql"],
    },
)
def sql_query(session: Session, sql: str) -> str:
    from app.config import settings

    conn = session.conn
    try:
        result = conn.execute(sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchmany(settings.max_result_rows)
    except Exception as e:
        return f"SQL ошибка: {e}"

    truncated = len(rows) == settings.max_result_rows
    out = [
        f"Результат: {len(rows)} строк"
        f"{' (достигнут лимит, уточни запрос)' if truncated else ''}",
        "",
        format_table(columns, rows),
    ]
    return "\n".join(out)
