from __future__ import annotations

from app.config import settings
from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="sql_query",
    description="Выполняет SQL-запрос к загруженным таблицам и подключённым БД. Для подключённых БД SQL выполняется в source DB (push-down) с авто-трансляцией диалекта. Read-only guard блокирует INSERT/UPDATE/DELETE/DROP. PII-колонки автоматически маскируются.",
    parameters={
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Валидный SQL (DuckDB синтаксис для локальных таблиц; для remote БД автоматически транслируется). Имена таблиц из списка загруженных/подключённых.",
            },
            "connection": {"type": "string", "description": "Имя подключения (необязательно, для remote БД)"},
            "format": {"type": "string", "description": "Формат: markdown | json | csv (по умолчанию markdown)"},
        },
        "required": ["sql"],
    },
)
def sql_query(session: Session, sql: str, connection: str = "", format: str = "markdown") -> str:
    import time
    from ..sql_guard import check_read_only
    from ..error_handler import format_error_response
    from ..logging_db import get_log_db
    from ..pii_detector import mask_row, get_pii_columns_for_table
    from ..engine import get_engine_for_session

    eng = get_engine_for_session(session)

    # Read-only guard
    allowed, reason = check_read_only(sql)
    if not allowed:
        get_log_db().log_query(
            tool="sql_query", sql=sql[:500], connection=connection,
            success=False, error=reason,
        )
        return reason

    # Определяем: есть ли remote-таблицы (push-down)
    use_remote = eng.has_remote_tables() or bool(connection)

    start = time.time()
    try:
        if use_remote:
            cols, rows = eng.execute_remote(sql, connector_name=connection)
        else:
            result = session.conn.execute(sql)
            cols = [d[0] for d in result.description]
            rows = result.fetchmany(settings.max_result_rows)
        duration_ms = int((time.time() - start) * 1000)

        # PII masking
        if settings.pii_masking and rows:
            pii_cols: list[dict] = []
            # ищем PII-колонки среди таблиц сессии по совпадению имён колонок
            matched_tables = set()
            for col_name in cols:
                for tname in eng.tables:
                    if tname in matched_tables:
                        continue
                    pii_info = get_pii_columns_for_table(tname)
                    if pii_info:
                        pii_cols = pii_info
                        matched_tables.add(tname)
                        break
                if pii_cols:
                    break
            if pii_cols:
                cols_meta = [{"name": c} for c in cols]
                rows = [mask_row(r, cols_meta, pii_cols) for r in rows]

        get_log_db().log_query(
            tool="sql_query", sql=sql[:500], connection=connection,
            rows_returned=len(rows), duration_ms=duration_ms, success=True,
        )

        if not use_remote:
            rows = list(rows)
            if len(rows) == settings.max_result_rows:
                truncated_note = " (достигнут лимит, уточни запрос)"
            else:
                truncated_note = ""
        else:
            # remote мог вернуть больше; ограничим
            if len(rows) > settings.max_result_rows:
                rows = rows[: settings.max_result_rows]
                truncated_note = " (достигнут лимит, уточни запрос)"
            else:
                truncated_note = ""

        if format == "json":
            import json
            return json.dumps(
                {"columns": cols, "rows": [list(r) for r in rows]},
                ensure_ascii=False,
                default=str,
            )
        if format == "csv":
            import csv
            import io
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(cols)
            writer.writerows(rows)
            return buf.getvalue()

        out = [
            f"Результат: {len(rows)} строк{truncated_note}",
            "",
            format_table(cols, rows),
        ]
        return "\n".join(out)

    except PermissionError as e:
        return str(e)
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        get_log_db().log_query(
            tool="sql_query", sql=sql[:500], connection=connection,
            duration_ms=duration_ms, success=False, error=str(e)[:500],
        )
        get_log_db().log_error(
            error_type="SQL", message=str(e)[:500], sql=sql[:500],
            connection=connection, tool="sql_query",
        )
        return format_error_response(e, context="sql_query")