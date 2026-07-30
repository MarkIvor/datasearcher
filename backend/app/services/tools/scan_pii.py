from __future__ import annotations

from app.config import settings
from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="scan_pii",
    description="Просканировать таблицу на наличие персональных данных (PII): email, телефон, ИНН, СНИЛС, паспорт, карта, IP. Помечает найденные колонки в Knowledge Base для авто-маскирования.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы для сканирования"},
        },
        "required": ["table_name"],
    },
)
def scan_pii(session: Session, table_name: str) -> str:
    from ..engine import get_engine_for_session
    from ..pii_detector import scan_table_for_pii
    eng = get_engine_for_session(session)

    ref = eng.get_table_ref(table_name)
    if ref is None and table_name not in {fi.table_name for fi in session.files.values()}:
        return f"Таблица '{table_name}' не найдена. Доступные: {sorted(eng.tables.keys())}"

    if ref and ref.connector_name and not ref.in_duckdb:
        # remote таблица — выгрузить sample
        connector = eng.get_connector_for_table(table_name)
        try:
            cols, rows = connector.fetch_table(ref.name, limit=settings.pii_scan_rows)
            col_info = [{"name": c, "type": "varchar"} for c in cols]
        except Exception as e:
            return f"Ошибка получения данных: {e}"
    else:
        try:
            desc = session.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
            col_info = [{"name": r[0], "type": r[1]} for r in desc]
            result = session.conn.execute(
                f'SELECT * FROM "{table_name}" LIMIT {settings.pii_scan_rows}'
            )
            rows = result.fetchall()
        except Exception as e:
            return f"Ошибка: {e}"

    if not rows:
        return "Нет данных для сканирования."

    pii_found = scan_table_for_pii(table_name, col_info, rows)
    if not pii_found:
        return f"✅ PII не обнаружено в таблице '{table_name}' (проверено {len(rows)} строк)."

    out = [
        f"🔍 Найдено PII в таблице '{table_name}':",
        "",
        format_table(["column", "pii_type"], [(p["column"], p["pii_type"]) for p in pii_found]),
        "",
        "Колонки помечены в Knowledge Base. Значения будут автоматически маскироваться в результатах SQL-запросов.",
    ]
    return "\n".join(out)