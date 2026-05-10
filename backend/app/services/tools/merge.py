from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="merge_tables",
    description="Умный JOIN двух таблиц: авто-детекция ключей по совпадению имён колонок и типов, выбор типа JOIN (inner/left/right/full), предпросмотр результата. Объединяет данные из двух загруженных файлов.",
    parameters={
        "type": "object",
        "properties": {
            "table_a": {"type": "string", "description": "Первая таблица"},
            "table_b": {"type": "string", "description": "Вторая таблица"},
            "join_type": {"type": "string", "enum": ["inner", "left", "right", "full"], "description": "Тип JOIN (по умолчанию inner)"},
            "key_columns": {"type": "string", "description": "Ключевые колонки через запятую (авто-детекция если не указаны)"},
            "output_table": {"type": "string", "description": "Имя новой таблицы (по умолчанию auto: merged_таблицы)"},
        },
        "required": ["table_a", "table_b"],
    },
)
def merge_tables(
    session: Session,
    table_a: str,
    table_b: str,
    join_type: str = "inner",
    key_columns: str = "",
    output_table: str = "",
) -> str:
    available = {fi.table_name for fi in session.files.values()}
    if table_a not in available:
        return f"Таблица '{table_a}' не найдена. Доступные: {sorted(available)}"
    if table_b not in available:
        return f"Таблица '{table_b}' не найдена. Доступные: {sorted(available)}"

    conn = session.conn
    schema_a = conn.execute(f'DESCRIBE "{table_a}"').fetchall()
    schema_b = conn.execute(f'DESCRIBE "{table_b}"').fetchall()

    cols_a = {s[0]: s[1] for s in schema_a}
    cols_b = {s[0]: s[1] for s in schema_b}

    if not key_columns.strip():
        common = set(cols_a.keys()) & set(cols_b.keys())
        if not common:
            name_matches = set()
            for ca in cols_a:
                for cb in cols_b:
                    if ca.lower().replace("_", "") == cb.lower().replace("_", ""):
                        name_matches.add((ca, cb))
            if name_matches:
                keys = list(name_matches)
            else:
                return f"Авто-детекция не нашла общих колонок.\nТаблица A: {list(cols_a.keys())}\nТаблица B: {list(cols_b.keys())}\nУкажите key_columns вручную."
        else:
            keys = [(c, c) for c in common]
    else:
        key_list = [k.strip() for k in key_columns.split(",")]
        keys = [(k, k) for k in key_list]

    if not output_table:
        output_table = f"merged_{table_a}_{table_b}"
    output_table = output_table.replace(" ", "_").replace("-", "_")

    join_cond = " AND ".join(f'a."{ka}" = b."{kb}"' for ka, kb in keys)

    select_parts = []
    for col_name, col_type in schema_a:
        select_parts.append(f'a."{col_name}" as "{table_a}_{col_name}"')
    for col_name, col_type in schema_b:
        if col_name not in set(cols_a.keys()):
            select_parts.append(f'b."{col_name}" as "{table_b}_{col_name}"')
        else:
            select_parts.append(f'b."{col_name}" as "{table_b}_{col_name}"')

    select_sql = ", ".join(select_parts)

    join_type_map = {"inner": "INNER JOIN", "left": "LEFT JOIN", "right": "RIGHT JOIN", "full": "FULL OUTER JOIN"}
    join_sql = join_type_map.get(join_type, "INNER JOIN")

    sql = f'SELECT {select_sql} FROM "{table_a}" a {join_sql} "{table_b}" b ON {join_cond}'

    try:
        preview = conn.execute(f'{sql} LIMIT 5')
        preview_cols = [d[0] for d in preview.description]
        preview_rows = preview.fetchall()
    except Exception as e:
        return f"Ошибка предпросмотра: {e}\n\nSQL: {sql}"

    try:
        conn.execute(f'CREATE TABLE "{output_table}" AS {sql}')
        count = conn.execute(f'SELECT COUNT(*) FROM "{output_table}"').fetchone()[0]
    except Exception as e:
        return f"Ошибка создания таблицы: {e}\n\nSQL: {sql}"

    count_a = conn.execute(f'SELECT COUNT(*) FROM "{table_a}"').fetchone()[0]
    count_b = conn.execute(f'SELECT COUNT(*) FROM "{table_b}"').fetchone()[0]

    out = [
        f"# Merge: {table_a} + {table_b} → {output_table}",
        "",
        f"Тип JOIN: {join_type.upper()}",
        f"Ключи: {', '.join(f'{ka}={kb}' for ka, kb in keys)}",
        f"Строк в {table_a}: {count_a:,}",
        f"Строк в {table_b}: {count_b:,}",
        f"Строк в результате: {count:,}",
        "",
        "Предпросмотр (первые 5 строк):",
        format_table(preview_cols, preview_rows),
        "",
        f"Таблица `{output_table}` создана и доступна для анализа.",
    ]

    return "\n".join(out)
