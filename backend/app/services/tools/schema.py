from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="get_schema",
    description="Возвращает структуру таблицы: колонки, типы, количество строк и превью данных. Вызывай ПЕРВЫМ перед любыми запросами, чтобы узнать названия колонок.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Имя таблицы (из списка загруженных файлов)",
            }
        },
        "required": ["table_name"],
    },
)
def get_schema(session: Session, table_name: str) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные таблицы: {available}"

    from app.config import settings

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
    preview = conn.execute(
        f'SELECT * FROM "{table_name}" LIMIT {settings.max_preview_rows}'
    ).fetchall()

    col_names = [x[0] for x in schema]
    out = [
        f"Таблица: {table_name}",
        f"Строк: {count:,}",
        "",
        "Колонки:",
        *[f"  - {x[0]}  [{x[1]}]" for x in schema],
        "",
        f"Превью ({settings.max_preview_rows} строк):",
        format_table(col_names, preview),
    ]
    return "\n".join(out)
