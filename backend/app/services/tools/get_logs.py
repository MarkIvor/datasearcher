from __future__ import annotations

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="get_logs",
    description="Показать логи запросов, ошибок или аудита. Используй для отладки и контроля кто что запрашивал.",
    parameters={
        "type": "object",
        "properties": {
            "log_type": {"type": "string", "description": "Тип лога: query | error | audit"},
            "limit": {"type": "integer", "description": "Сколько записей показать (по умолчанию 20)"},
        },
    },
)
def get_logs(session: Session, log_type: str = "query", limit: int = 20) -> str:
    from ..logging_db import get_log_db
    log_db = get_log_db()

    if log_type == "error":
        logs = log_db.get_error_logs(limit)
        if not logs:
            return "Логи ошибок пусты."
        rows = [
            (l.get("timestamp", "")[:19], l.get("error_type", ""), l.get("message", "")[:80])
            for l in logs
        ]
        return f"Логи ошибок ({len(rows)}):\n\n" + format_table(
            ["timestamp", "error_type", "message"], rows
        )

    if log_type == "audit":
        logs = log_db.get_audit_logs(limit)
        if not logs:
            return "Логи аудита пусты."
        rows = [
            (l.get("timestamp", "")[:19], l.get("action", ""), l.get("target", ""))
            for l in logs
        ]
        return f"Логи аудита ({len(rows)}):\n\n" + format_table(
            ["timestamp", "action", "target"], rows
        )

    logs = log_db.get_query_logs(limit)
    if not logs:
        return "Логи запросов пусты."
    rows = [
        (
            l.get("timestamp", "")[:19],
            l.get("tool", ""),
            l.get("table_name", ""),
            l.get("duration_ms", 0),
            "✓" if l.get("success") else "✗",
        )
        for l in logs
    ]
    return f"Логи запросов ({len(rows)}):\n\n" + format_table(
        ["timestamp", "tool", "table", "ms", "ok"], rows
    )