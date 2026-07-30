from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="sample_data",
    description="Получить случайную выборку строк из таблицы. Полезно для понимания содержания данных, проверки качества, или когда нужно быстро посмотреть данные.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Имя таблицы",
            },
            "n": {
                "type": "integer",
                "description": "Количество строк выборки (по умолчанию 10, макс 50)",
            },
            "where": {
                "type": "string",
                "description": "SQL WHERE условие для фильтрации (необязательно)",
            },
            "method": {
                "type": "string",
                "enum": ["random", "first", "last", "stratified"],
                "description": "Метод выборки: random — случайные, first — первые, last — последние, stratified — стратифицированная по колонке",
            },
            "stratify_column": {
                "type": "string",
                "description": "Колонка для стратифицированной выборки (только если method=stratified)",
            },
        },
        "required": ["table_name"],
    },
)
def sample_data(
    session: Session,
    table_name: str,
    n: int = 10,
    where: str = "",
    method: str = "random",
    stratify_column: str = "",
) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    from .registry import format_table

    conn = session.conn
    n = min(max(n, 1), 50)

    where_clause = f" WHERE {where}" if where.strip() else ""

    if method == "stratified" and stratify_column:
        total = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"{where_clause}').fetchone()[0]
        if total == 0:
            return "Нет данных для выборки."

        values = conn.execute(
            f'SELECT DISTINCT "{stratify_column}" FROM "{table_name}"{where_clause} LIMIT 20'
        ).fetchall()
        if not values:
            return "Нет уникальных значений для стратификации."

        per_group = max(1, n // len(values))
        union_parts = []
        for (val,) in values:
            val_escaped = str(val).replace("'", "''") if val is not None else "NULL"
            is_null = val is None
            cond = f'"{stratify_column}" IS NULL' if is_null else f"\"{stratify_column}\" = '{val_escaped}'"
            base_where = f"({cond})" + (f" AND ({where})" if where.strip() else "")
            union_parts.append(
                f'SELECT * FROM "{table_name}" WHERE {base_where} LIMIT {per_group}'
            )
        sql = " UNION ALL ".join(union_parts)
    elif method == "random":
        sql = f'SELECT * FROM "{table_name}"{where_clause} ORDER BY RANDOM() LIMIT {n}'
    elif method == "last":
        sql = f'SELECT * FROM "{table_name}"{where_clause} ORDER BY rowid DESC LIMIT {n}'
    else:
        sql = f'SELECT * FROM "{table_name}"{where_clause} LIMIT {n}'

    try:
        result = conn.execute(sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchall()
    except Exception as e:
        return f"SQL ошибка: {e}"

    if not rows:
        return "Нет данных для выборки."

    return f"Выборка ({method}, {len(rows)} строк):\n\n{format_table(columns, rows)}"
