from __future__ import annotations

import os

from app.session import Session
from .registry import register_tool


@register_tool(
    name="load_file",
    description="Загрузить файл данных (CSV, Excel .xlsx, Parquet) в текущую сессию для анализа. Возвращает имя таблицы и количество строк.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Путь к файлу на сервере"},
            "table_name": {"type": "string", "description": "Имя таблицы (необязательно, по умолчанию = имя файла)"},
            "sheet": {"type": "string", "description": "Имя листа Excel (необязательно, по умолчанию все листы)"},
        },
        "required": ["path"],
    },
)
def load_file(session: Session, path: str, table_name: str = "", sheet: str = "") -> str:
    from ..engine import get_engine_for_session
    eng = get_engine_for_session(session)

    if not os.path.isfile(path):
        return f"❌ Файл не найден: {path}"

    lower = path.lower()
    if lower.endswith(".parquet"):
        fi = eng.load_parquet(path, table_name)
        if fi:
            return f"✅ Загружен Parquet: таблица '{fi.table_name}', {fi.row_count} строк, {len(fi.columns)} колонок."
        return f"❌ Не удалось загрузить {path}. {eng.errors()[-1] if eng.errors() else ''}"

    if lower.endswith((".xlsx", ".xls")):
        results = eng.load_excel(path, table_name, sheet)
        if not results:
            return f"❌ Не удалось загрузить Excel. {eng.errors()[-1] if eng.errors() else ''}"
        lines = ["✅ Загружен Excel:"]
        for fi in results:
            lines.append(f"  - {fi.table_name}: {fi.row_count} строк, {len(fi.columns)} колонок")
        return "\n".join(lines)

    fi = eng.load_csv(path, table_name)
    if fi:
        return f"✅ Загружен CSV: таблица '{fi.table_name}', {fi.row_count} строк, {len(fi.columns)} колонок."
    return f"❌ Не удалось загрузить {path}. {eng.errors()[-1] if eng.errors() else ''}"