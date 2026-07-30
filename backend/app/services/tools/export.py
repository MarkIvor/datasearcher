from __future__ import annotations

import csv
import io
import os
import tempfile

from app.session import Session
from .registry import register_tool


@register_tool(
    name="export_data",
    description="Экспорт данных: скачать результат как CSV файл. Можно отфильтровать и выбрать колонки перед экспортом. Возвращает URL для скачивания.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы для экспорта"},
            "sql": {"type": "string", "description": "SQL-запрос для фильтрации (необязательно, экспорт всей таблицы если не указан)"},
            "columns": {"type": "string", "description": "Колонки для экспорта через запятую (необязательно, все если не указаны)"},
            "filename": {"type": "string", "description": "Имя файла (по умолчанию таблица.csv)"},
        },
        "required": ["table_name"],
    },
)
def export_data(session: Session, table_name: str, sql: str = "", columns: str = "", filename: str = "") -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn

    if not filename:
        filename = f"{table_name}.csv"
    if not filename.endswith(".csv"):
        filename += ".csv"

    if sql.strip():
        query = sql.strip()
    elif columns.strip():
        cols = ", ".join(f'"{c.strip()}"' for c in columns.split(","))
        query = f'SELECT {cols} FROM "{table_name}"'
    else:
        query = f'SELECT * FROM "{table_name}"'

    try:
        result = conn.execute(query)
        col_names = [d[0] for d in result.description]
        rows = result.fetchall()
    except Exception as e:
        return f"Ошибка запроса: {e}"

    if not rows:
        return "Нет данных для экспорта."

    export_dir = os.path.join(tempfile.gettempdir(), "datasearcher_exports")
    os.makedirs(export_dir, exist_ok=True)

    filepath = os.path.join(export_dir, f"{session.id}_{filename}")

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(col_names)
        writer.writerows(rows)

    if not hasattr(session, "_exports"):
        session._exports = {}
    export_id = f"exp_{len(session._exports)}"
    session._exports[export_id] = filepath

    return (
        f"__EXPORT_DATA__\n"
        f"export_id={export_id}\n"
        f"filename={filename}\n"
        f"rows={len(rows)}\n"
        f"columns={len(col_names)}\n"
        f"__END_EXPORT_DATA__"
    )
