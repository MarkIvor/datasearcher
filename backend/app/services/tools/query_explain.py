from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="query_explain",
    description="Показать план выполнения SQL (EXPLAIN) для оптимизации запроса. Используй для тяжёлых запросов к подключённым БД.",
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "SQL-запрос для анализа плана"},
            "connection": {"type": "string", "description": "Имя подключения (необязательно)"},
        },
        "required": ["sql"],
    },
)
def query_explain(session: Session, sql: str, connection: str = "") -> str:
    from ..engine import get_engine_for_session
    eng = get_engine_for_session(session)

    try:
        connector = eng.get_connector_by_name(connection) if connection else None
        if connector is None:
            connector = next(iter(eng.connectors.values()), None)

        if connector is not None:
            translated = eng.translate_sql(sql, connector.name)
            cols, rows = connector.execute_sql(f"EXPLAIN {translated}")
            lines = ["План выполнения (source DB):", ""]
            for row in rows:
                lines.append(" | ".join(str(v) for v in row))
            return "\n".join(lines)

        # Иначе — DuckDB EXPLAIN
        result = session.conn.execute(f"EXPLAIN {sql}")
        lines = ["План выполнения (DuckDB):", ""]
        for row in result.fetchall():
            lines.append(f"{row[0]}: {row[1]}")
        return "\n".join(lines)
    except Exception as e:
        from ..error_handler import format_error_response
        return format_error_response(e, context="query_explain")