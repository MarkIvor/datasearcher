from __future__ import annotations

import os
import tempfile

from app.config import settings
from app.session import Session
from .registry import register_tool


@register_tool(
    name="export_xlsx",
    description="Экспорт данных в XLSX с форматированием: жирные заголовки, freeze panes, авто-ширина, автофильтр, NULL → серый фон. Возвращает ссылку для скачивания.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы для экспорта"},
            "sql": {"type": "string", "description": "SQL-запрос для фильтрации (необязательно)"},
            "columns": {"type": "string", "description": "Колонки через запятую (необязательно)"},
            "filename": {"type": "string", "description": "Имя файла (по умолчанию таблица.xlsx)"},
        },
        "required": ["table_name"],
    },
)
def export_xlsx(
    session: Session,
    table_name: str,
    sql: str = "",
    columns: str = "",
    filename: str = "",
) -> str:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        return "Для XLSX-экспорта нужен openpyxl: pip install openpyxl"

    from ..engine import get_engine_for_session
    eng = get_engine_for_session(session)

    # Если таблица remote — выгрузить в DuckDB
    ref = eng.get_table_ref(table_name)
    if ref and ref.connector_name and not ref.in_duckdb:
        try:
            eng.ensure_table_in_duckdb(table_name)
        except Exception as e:
            return f"Не удалось выгрузить remote-таблицу: {e}"

    conn = session.conn
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

    if not filename:
        filename = f"{table_name}.xlsx"
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"

    export_dir = settings.exports_dir or os.path.join(
        tempfile.gettempdir(), "datasearcher_exports"
    )
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, f"{session.id}_{filename}")

    wb = Workbook()
    ws = wb.active
    ws.title = table_name[:31]

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
    null_fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")

    for col_idx, col_name in enumerate(col_names, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, row in enumerate(rows, 2):
        for col_idx, val in enumerate(row, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            if val is None:
                cell.value = ""
                cell.fill = null_fill
            else:
                cell.value = val

    for col_idx, col_name in enumerate(col_names, 1):
        max_len = len(str(col_name))
        for row_idx in range(2, min(len(rows) + 2, 102)):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 50)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(col_names))}{len(rows) + 1}"

    wb.save(filepath)

    if not hasattr(session, "_exports"):
        session._exports = {}
    export_id = f"xlsx_{len(session._exports)}"
    session._exports[export_id] = filepath

    return (
        f"__EXPORT_DATA__\n"
        f"export_id={export_id}\n"
        f"filename={filename}\n"
        f"rows={len(rows)}\n"
        f"columns={len(col_names)}\n"
        f"format=xlsx\n"
        f"__END_EXPORT_DATA__"
    )