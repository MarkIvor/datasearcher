from __future__ import annotations

from app.config import settings
from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="get_schema",
    description="Возвращает структуру таблицы: колонки, типы, количество строк и превью данных. Для remote-таблиц (подключённые БД) читает схему из source DB. Обогащается метаданными из Knowledge Base (описания, PII).",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Имя таблицы (из списка загруженных файлов или подключённых БД)",
            }
        },
        "required": ["table_name"],
    },
)
def get_schema(session: Session, table_name: str) -> str:
    from ..engine import get_engine_for_session
    from ..knowledge_base import get_kb
    from ..pii_detector import get_pii_columns_for_table
    eng = get_engine_for_session(session)

    ref = eng.get_table_ref(table_name)
    if ref is None and table_name not in {fi.table_name for fi in session.files.values()}:
        available = sorted(eng.tables.keys()) or [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные таблицы: {available}"

    # remote таблица — читаем схему из source DB
    if ref and ref.connector_name and not ref.in_duckdb:
        connector = eng.get_connector_for_table(table_name)
        try:
            col_info = ref.columns or connector.describe(ref.name)
            count = ref.row_count if ref.row_count else connector.row_count(ref.name)
            # preview из source
            try:
                cols, rows = connector.fetch_table(ref.name, limit=settings.max_preview_rows)
                preview_cols = cols
                preview_rows = rows
            except Exception:
                preview_cols = [c["name"] for c in col_info]
                preview_rows = []
        except Exception as e:
            return f"Ошибка чтения схемы из source БД: {e}"
    else:
        conn = session.conn
        schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
        col_info = [{"name": x[0], "type": x[1]} for x in schema]
        count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        preview = conn.execute(
            f'SELECT * FROM "{table_name}" LIMIT {settings.max_preview_rows}'
        ).fetchall()
        preview_cols = [x[0] for x in schema]
        preview_rows = preview

    col_names = [c["name"] for c in col_info]

    out = [
        f"Таблица: {table_name}",
        f"Строк: {count:,}",
    ]

    # Обогащение из KB
    kb_table = get_kb().get_table(table_name)
    if kb_table:
        if kb_table.get("description"):
            out.append(f"Описание: {kb_table['description']}")
        if kb_table.get("owner"):
            out.append(f"Владелец: {kb_table['owner']}")
        if kb_table.get("layer"):
            out.append(f"Слой: {kb_table['layer']}")
        if kb_table.get("is_certified"):
            out.append("✅ Сертифицирована")

    out.append("")
    out.append("Колонки:")

    # PII-метки
    pii_cols = get_pii_columns_for_table(table_name) if settings.pii_masking else []
    pii_map = {p["column"]: p["pii_type"] for p in pii_cols} if pii_cols else {}

    kb_cols = {c["column_name"]: c for c in get_kb().get_columns(table_name)}

    for c in col_info:
        line = f"  - {c['name']}  [{c.get('type', '?')}]"
        marks = []
        if c["name"] in pii_map:
            marks.append(f"🔒 PII:{pii_map[c['name']]}")
        kb_c = kb_cols.get(c["name"])
        if kb_c and kb_c.get("description"):
            marks.append(f"«{kb_c['description'][:50]}»")
        if marks:
            line += "  " + " ".join(marks)
        out.append(line)

    if preview_rows:
        out.append("")
        out.append(f"Превью ({settings.max_preview_rows} строк):")
        out.append(format_table(preview_cols, preview_rows))

    return "\n".join(out)