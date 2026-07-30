from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="generate_sql",
    description="Генерация SQL-запроса из описания на естественном языке. Получает схему таблицы и описание того, что нужно, и создаёт валидный DuckDB SQL. Возвращает и запрос, и объяснение логики. Можно выполнить сразу через sql_query.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "description": {"type": "string", "description": "Описание на естественном языке того, какой анализ нужен"},
            "execute": {"type": "boolean", "description": "Выполнить сгенерированный запрос сразу (по умолчанию true)"},
        },
        "required": ["table_name", "description"],
    },
)
def generate_sql(session: Session, table_name: str, description: str, execute: bool = True) -> str:
    if table_name not in {fi.table_name for fi in session.files.values()}:
        available = [fi.table_name for fi in session.files.values()]
        return f"Таблица '{table_name}' не найдена. Доступные: {available}"

    conn = session.conn
    schema = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
    count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    schema_desc = ", ".join(f"{s[0]} ({s[1]})" for s in schema)

    sample = conn.execute(f'SELECT * FROM "{table_name}" LIMIT 3').fetchall()
    col_names = [s[0] for s in schema]
    from .registry import format_table
    sample_str = format_table(col_names, sample)

    return (
        f"__GENERATE_SQL_TASK__\n"
        f"table_name={table_name}\n"
        f"schema={schema_desc}\n"
        f"row_count={count}\n"
        f"sample={sample_str}\n"
        f"description={description}\n"
        f"execute={'true' if execute else 'false'}\n"
        f"__END_GENERATE_SQL_TASK__"
    )
