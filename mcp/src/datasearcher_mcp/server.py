from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .config import settings
from .engine import AnalysisEngine
from .llm_client import get_llm_client
from .render.charts import render_chart_png
from .render.markers import collect_charts, extract_marker
from .tools.registry import TOOL_HANDLERS

engine: AnalysisEngine | None = None

def _get_engine() -> AnalysisEngine:
    global engine
    if engine is None:
        engine = AnalysisEngine()
    return engine

# ───────────────────────────────────────────────
# Sampling helper (фича E)
# ───────────────────────────────────────────────
_sampling_ctx: dict = {}

def set_sampling_context(request_fn):
    _sampling_ctx["request"] = request_fn

async def _llm_via_sampling(messages: list[dict]) -> str:
    request_fn = _sampling_ctx.get("request")
    if request_fn is None:
        raise RuntimeError("MCP sampling недоступен")
    result = await request_fn(messages=messages, max_tokens=settings.llm_max_tokens)
    if hasattr(result, "content"):
        c = result.content
        return c.text if hasattr(c, "text") else str(c)
    return str(result)

@asynccontextmanager
async def lifespan(app):
    global engine
    eng = _get_engine()
    cfg = os.path.abspath(settings.connections_file)
    if os.path.isfile(cfg):
        eng.load_config(cfg)
    yield

mcp = FastMCP("DataSearcher", lifespan=lifespan)

# ───────────────────────────────────────────────
# Постобработка результатов
# ───────────────────────────────────────────────
async def _postprocess(result: str, tool_name: str) -> str:
    if not isinstance(result, str):
        return str(result)

    if result.startswith("__CLASSIFY_TASK__"):
        llm = get_llm_client()
        mode = settings.llm_mode.lower()
        if mode == "sampling" and _sampling_ctx.get("request"):
            return await _classify_via_sampling(result)
        if mode == "builtin" and llm.enabled:
            return await llm.handle_classify(_get_engine().session, result)
        return (
            "classify_rows требует LLM. Настройте llm_mode=sampling (модель хоста) "
            "или llm_mode=builtin с LLM_BASE_URL/LLM_MODEL.\n\nДанные:\n" + result
        )

    if result.startswith("__GENERATE_SQL_TASK__"):
        llm = get_llm_client()
        mode = settings.llm_mode.lower()
        if mode == "sampling" and _sampling_ctx.get("request"):
            return await _generate_sql_via_sampling(result)
        if mode == "builtin" and llm.enabled:
            return await llm.handle_generate_sql(_get_engine().session, result)
        description = extract_marker(result, "description=", "\n")
        return (
            "generate_sql требует LLM (llm_mode=sampling или builtin). "
            "Используйте sql_query напрямую. Описание: " + description + "\n\n" + result
        )

    if result.startswith("__DASHBOARD_CREATED__"):
        dash_json = extract_marker(result, "__DASHBOARD_CREATED__", "__END_DASHBOARD_CREATED__")
        if dash_json:
            try:
                info = json.loads(dash_json)
                return (
                    f"✅ Дашборд «{info.get('title', '')}» создан!\n\n"
                    f"📁 HTML-файл: {info.get('path', '')}\n"
                    f"Виджетов: {info.get('cards', '?')}, фильтров: {info.get('selectors', '?')}\n\n"
                    f"Откройте файл в браузере (нужен интернет для DuckDB-WASM и Chart.js)."
                )
            except json.JSONDecodeError:
                pass
        return result

    charts, clean = collect_charts(result)
    if charts:
        eng = _get_engine()
        mode = settings.charts_mode.lower()
        notes: list[str] = []
        for i, chart in enumerate(charts):
            title = chart.get("title", f"chart_{i}")
            n = len(chart.get("data", []))
            line = f"📊 **{title}** ({chart.get('type', '')}, {n} точек)"
            if mode in ("png", "both"):
                path = render_chart_png(chart, eng.charts_dir, i)
                if path:
                    line += f" → PNG: `{path}`"
            notes.append(line)
            if mode in ("json", "both"):
                notes.append("```json\n" + json.dumps(chart, ensure_ascii=False, default=str)[:4000] + "\n```")
        return clean + "\n\n--- Графики ---\n" + "\n\n".join(notes)

    if result.startswith("__EXPORT_DATA__"):
        export_info = extract_marker(result, "__EXPORT_DATA__", "__END_EXPORT_DATA__")
        if export_info:
            data: dict[str, str] = {}
            for line in export_info.split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k] = v
            export_id = data.get("export_id", "")
            eng = _get_engine()
            filepath = eng.session._exports.get(export_id, "") if hasattr(eng.session, "_exports") else ""
            return (
                f"✅ Экспорт готов: **{data.get('filename', '')}**\n"
                f"📁 Файл: `{filepath}`\n"
                f"Строк: {data.get('rows', '?')}, колонок: {data.get('columns', '?')}"
            )

    return result

# ───────────────────────────────────────────────
# Sampling-реализации (фича E)
# ───────────────────────────────────────────────
async def _classify_via_sampling(task_data: str) -> str:
    from .prompts.system import build_classify_prompt
    import json as _json

    params: dict[str, str] = {}
    data_json = ""
    for line in task_data.split("\n"):
        if line in ("__CLASSIFY_TASK__", "__END_CLASSIFY_TASK__"):
            continue
        if line.startswith("data="):
            data_json = line[5:]
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            params[k] = v

    columns = _json.loads(params.get("columns", "[]"))
    categories = _json.loads(params.get("categories", "[]"))
    instruction = params.get("instruction", "")
    table_name = params.get("table_name", "")
    row_ids = _json.loads(params.get("row_ids", "[]"))
    data_rows = _json.loads(data_json) if data_json else []

    if not data_rows:
        return "Нет данных для классификации."

    prompt = build_classify_prompt(categories, instruction, columns)
    batch_size = settings.classify_batch_size
    all_results: list[dict] = []

    for i in range(0, len(data_rows), batch_size):
        batch = data_rows[i:i + batch_size]
        batch_with_index = []
        for j, row in enumerate(batch):
            row_dict = {columns[k]: v for k, v in enumerate(row) if k < len(columns)}
            row_dict["_row_index"] = i + j
            batch_with_index.append(row_dict)
        try:
            result_text = await _llm_via_sampling([
                {"role": "system", "content": prompt},
                {"role": "user", "content": _json.dumps(batch_with_index, ensure_ascii=False, default=str)},
            ])
            try:
                parsed = _json.loads(result_text)
                if isinstance(parsed, list):
                    all_results.extend(parsed)
            except _json.JSONDecodeError:
                all_results.append({"raw_response": result_text, "batch": i})
        except Exception as e:
            all_results.append({"error": str(e), "batch": i})

    if not all_results:
        return "Классификация не удалась."

    summary: dict[str, int] = {}
    for r in all_results:
        cat = r.get("category", "unknown")
        summary[cat] = summary.get(cat, 0) + 1

    out = [f"Классификация завершена ({len(all_results)} строк):", "", "Распределение:"]
    for cat, cnt in sorted(summary.items(), key=lambda x: -x[1]):
        pct = round(cnt / len(all_results) * 100, 1)
        out.append(f"  {cat}: {cnt} ({pct}%)")

    if table_name and row_ids and all_results:
        try:
            eng = _get_engine()
            conn = eng.session.conn
            conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS _classification VARCHAR DEFAULT NULL')
            for r in all_results:
                idx = r.get("row_index")
                cat = r.get("category")
                if idx is not None and cat and idx < len(row_ids):
                    conn.execute(f'UPDATE "{table_name}" SET _classification = ? WHERE rowid = ?', [cat, row_ids[idx]])
            out.append(f"\nРезультаты записаны в колонку _classification таблицы {table_name}.")
        except Exception as e:
            out.append(f"\nНе удалось записать: {e}")

    return "\n".join(out)

async def _generate_sql_via_sampling(task_data: str) -> str:
    from .prompts.system import build_generate_sql_prompt
    import json as _json

    params: dict[str, str] = {}
    for line in task_data.split("\n"):
        if line.startswith("__GENERATE_SQL_TASK__") or line.startswith("__END_GENERATE_SQL_TASK__"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            params[k] = v

    schema_desc = params.get("schema", "")
    sample = params.get("sample", "")
    description = params.get("description", "")
    table_name = params.get("table_name", "")
    execute = params.get("execute", "true") == "true"

    if not description:
        return "Не указано описание для генерации SQL."

    prompt = build_generate_sql_prompt(schema_desc, sample, description)
    try:
        result_text = await _llm_via_sampling([
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Сгенерируй SQL для: {description}"},
        ])
    except Exception as e:
        return f"Ошибка sampling: {e}"

    try:
        parsed = _json.loads(result_text)
        sql = parsed.get("sql", "")
        explanation = parsed.get("explanation", "")
    except _json.JSONDecodeError:
        sql = result_text.strip()
        explanation = ""

    if not sql:
        return "Не удалось сгенерировать SQL."

    out = [
        f"Сгенерированный SQL для таблицы {table_name}:",
        "",
        f"**Объяснение:** {explanation}" if explanation else "",
        f"```sql\n{sql}\n```",
    ]

    if execute and sql and table_name:
        try:
            eng = _get_engine()
            conn = eng.session.conn
            query_result = conn.execute(sql)
            if query_result.description:
                cols = [d[0] for d in query_result.description]
                rows = query_result.fetchmany(200)
                from .tools.registry import format_table
                out.append(f"\nРезультат ({len(rows)} строк):")
                out.append(format_table(cols, rows))
            else:
                out.append("\nЗапрос выполнен успешно.")
        except Exception as e:
            out.append(f"\nОшибка выполнения: {e}")

    return "\n".join(out)

# ───────────────────────────────────────────────
# Утилиты выполнения
# ───────────────────────────────────────────────
async def _run(tool_name: str, **kwargs) -> str:
    """Выполнить инструмент с rate limiting, error handling, logging (ТЗ v1)."""
    from .rate_limiter import check_rate_limit, rate_limit_message
    from .error_handler import format_error_response
    from .logging_db import get_log_db
    from .config import settings as cfg

    # Rate limiting (ТЗ 11)
    allowed, wait = check_rate_limit(tool_name)
    if not allowed:
        return rate_limit_message(tool_name, wait)

    handler = TOOL_HANDLERS[tool_name]

    import time
    start = time.time()
    try:
        result = handler(_get_engine().session, **kwargs)
        duration_ms = int((time.time() - start) * 1000)

        # Логирование (ТЗ 9)
        get_log_db().log_query(
            tool=tool_name,
            table_name=kwargs.get("table_name", ""),
            duration_ms=duration_ms,
            success=True,
        )

        return await _postprocess(result, tool_name)

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        get_log_db().log_query(
            tool=tool_name,
            table_name=kwargs.get("table_name", ""),
            duration_ms=duration_ms,
            success=False,
            error=str(e)[:500],
        )
        get_log_db().log_error(
            error_type=type(e).__name__,
            message=str(e)[:500],
            tool=tool_name,
        )
        return format_error_response(e, context=tool_name)

def _resolve_table_for_duckdb(table_name: str, columns: str = "", where: str = "", limit: int = 50000) -> str:
    """Гарантировать что таблица в DuckDB (для ML-инструментов)."""
    eng = _get_engine()
    ref = eng.get_table_ref(table_name)
    if ref is None:
        if table_name in eng.session.available_tables():
            return table_name
        raise ValueError(f"Таблица '{table_name}' не найдена. Доступные: {sorted(eng.tables.keys())}")
    if ref.in_duckdb and not columns:
        return ref.table_name
    return eng.ensure_table_in_duckdb(table_name, columns=columns, where=where, limit=limit)

def _progress(ctx, message: str):
    """Отправить progress notification (фича H)."""
    try:
        if ctx is not None:
            ctx.info(message)
    except Exception:
        pass

# ───────────────────────────────────────────────
# Инструменты: SQL и схема
# ───────────────────────────────────────────────

@mcp.tool()
async def sql_query(
    sql: str,
    connection: str = "",
    format: Literal["markdown", "json", "csv"] = "markdown",
    limit: int = 0,
) -> str:
    """Выполняет SQL-запрос (read-only). По умолчанию — push-down к source DB (remote).
    SQL пишется в DuckDB-синтаксисе, автоматически переводится под диалект source DB (sqlglot).
    Read-only: INSERT/UPDATE/DELETE/DROP заблокированы.
    format: markdown (по умолчанию), json, csv. limit: ограничение строк (0 = default 200).
    """
    from .sql_guard import check_read_only
    from .error_handler import format_error_response
    from .rate_limiter import check_rate_limit, rate_limit_message
    from .logging_db import get_log_db
    from .pii_detector import get_pii_columns_for_table, mask_row

    # Rate limiting (ТЗ 11)
    allowed_rl, wait = check_rate_limit("sql_query")
    if not allowed_rl:
        return rate_limit_message("sql_query", wait)

    # Read-only guard (ТЗ 2.1)
    allowed, reason = check_read_only(sql)
    if not allowed:
        get_log_db().log_error("Read-only blocked", reason[:300], sql=sql[:300], tool="sql_query")
        return reason

    eng = _get_engine()
    max_rows = limit if limit > 0 else settings.max_result_rows

    import time
    start = time.time()

    # Проверяем: если SQL ссылается на таблицы в DuckDB — выполняем там
    duckdb_tables = eng.session.available_tables() if eng.duckdb_enabled else set()
    sql_lower = sql.lower()
    uses_duckdb = any(f'"{t}"' in sql_lower or f" {t} " in sql_lower or f" {t}\n" in sql_lower
                      for t in duckdb_tables)

    try:
        if uses_duckdb and eng.duckdb_enabled:
            handler = TOOL_HANDLERS["sql_query"]
            result = handler(eng.session, sql=sql)
            duration_ms = int((time.time() - start) * 1000)
            get_log_db().log_query("sql_query", sql[:500], duration_ms=duration_ms, success=True)
            return await _postprocess(result, "sql_query")

        # Remote: push-down к source DB
        if eng.connectors:
            cols, rows = eng.execute_remote(sql, connector_name=connection)
            duration_ms = int((time.time() - start) * 1000)
            truncated = len(rows) > max_rows
            rows = rows[:max_rows]

            # PII masking (ТЗ 10)
            if settings.pii_masking and rows:
                for tname in eng.tables:
                    pii_cols = get_pii_columns_for_table(tname)
                    if pii_cols:
                        col_names = cols
                        pii_map = {pc["column_name"]: pc["pii_type"] for pc in pii_cols}
                        from .pii_detector import mask_value
                        masked_rows = []
                        for row in rows:
                            masked = list(row)
                            for i, cn in enumerate(col_names):
                                if cn in pii_map and i < len(masked):
                                    masked[i] = mask_value(masked[i], pii_map[cn])
                            masked_rows.append(tuple(masked))
                        rows = masked_rows
                        break

            get_log_db().log_query(
                "sql_query_remote", sql[:500], connection=connection,
                rows_returned=len(rows), duration_ms=duration_ms, success=True,
            )
            return _format_result(cols, rows, format, truncated, "remote")

        # Fallback: DuckDB
        if eng.duckdb_enabled:
            handler = TOOL_HANDLERS["sql_query"]
            result = handler(eng.session, sql=sql)
            duration_ms = int((time.time() - start) * 1000)
            get_log_db().log_query("sql_query", sql[:500], duration_ms=duration_ms, success=True)
            return await _postprocess(result, "sql_query")

        return "Нет доступных БД. Настройте connections.yaml или загрузите файл."

    except PermissionError as e:
        return str(e)
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        get_log_db().log_query("sql_query", sql[:500], duration_ms=duration_ms, success=False, error=str(e)[:300])
        get_log_db().log_error("SQL Error", str(e)[:500], sql=sql[:500], connection=connection, tool="sql_query")
        return format_error_response(e, context="sql_query")


def _format_result(cols: list[str], rows: list[tuple], fmt: str, truncated: bool, source: str) -> str:
    """Форматирование результата SQL (D2)."""
    from .tools.registry import format_table
    import csv as csv_mod
    import io

    header = f"Результат ({source}): {len(rows)} строк" + (" (достигнут лимит)" if truncated else "")

    if fmt == "json":
        data = [dict(zip(cols, row)) for row in rows]
        return header + "\n\n```json\n" + json.dumps(data, ensure_ascii=False, default=str, indent=2)[:20000] + "\n```"
    elif fmt == "csv":
        buf = io.StringIO()
        writer = csv_mod.writer(buf, delimiter=";")
        writer.writerow(cols)
        writer.writerows(rows)
        return header + "\n\n```csv\n" + buf.getvalue() + "```"
    else:  # markdown
        return header + "\n\n" + format_table(cols, rows)

@mcp.tool()
async def query_explain(sql: str, connection: str = "") -> str:
    """Показать план выполнения SQL (EXPLAIN) и стоимость. Полезно перед
    тяжёлыми запросами к удалённой БД. (фича G)
    """
    eng = _get_engine()

    # Для remote БД
    if eng.connectors and connection:
        connector = eng.get_connector_by_name(connection)
        if connector:
            try:
                cols, rows = connector.execute_sql(f"EXPLAIN {sql}")
                out = [f"План выполнения (remote, {connection}):", ""]
                for row in rows:
                    out.append("  " + " | ".join(str(v) for v in row))
                return "\n".join(out)
            except Exception as e:
                return f"EXPLAIN недоступен: {e}"

    # Для DuckDB
    if eng.duckdb_enabled:
        try:
            result = eng.session.conn.execute(f"EXPLAIN {sql}")
            rows = result.fetchall()
            out = ["План выполнения (DuckDB):", ""]
            for row in rows:
                out.append(f"  {row[0]}: {row[1] if len(row) > 1 else ''}")
            return "\n".join(out)
        except Exception as e:
            return f"EXPLAIN ошибка: {e}"

    return "Нет доступных БД для EXPLAIN."

@mcp.tool()
async def get_schema(table_name: str) -> str:
    """Структура таблицы: колонки, типы, число строк, превью."""
    eng = _get_engine()
    ref = eng.get_table_ref(table_name)

    # Если в DuckDB — используем оригинальный инструмент
    if ref and ref.in_duckdb:
        return await _run("get_schema", table_name=table_name)

    # Remote: берём схему из TableRef
    if ref:
        out = [
            f"Таблица: {table_name}",
            f"Строк: {ref.row_count:,}",
            f"Источник: {ref.source}",
            "",
            "Колонки:",
            *[f"  - {c['name']}  [{c['type']}]" for c in ref.columns],
        ]
        # Превью через remote
        try:
            connector = eng.get_connector_for_table(table_name)
            if connector:
                q = connector.quote(ref.name)
                cols, rows = connector.execute_sql(f"SELECT * FROM {q} LIMIT {settings.max_preview_rows}")
                from .tools.registry import format_table
                out.append(f"\nПревью ({settings.max_preview_rows} строк):")
                out.append(format_table(cols, rows))
        except Exception:
            pass
        return "\n".join(out)

    # Fallback на DuckDB
    return await _run("get_schema", table_name=table_name)

@mcp.tool()
async def attach_database(
    name: str,
    db_type: str,
    host: str = "",
    port: int = 0,
    database: str = "",
    username: str = "",
    password: str = "",
    mode: Literal["remote", "dump", "auto"] = "auto",
) -> str:
    """Подключить новую БД в рантайме без перезапуска сервера. (фича B)
    Поддерживаемые db_type: postgresql, mysql, clickhouse, sqlite.
    mode: remote (push-down SQL), dump (выгрузка в DuckDB), auto (по умолчанию).
    """
    eng = _get_engine()
    params = {
        "host": host, "port": port, "database": database,
        "username": username, "password": password,
    }
    try:
        added, errs = eng.attach_connector(name, db_type, params, mode=mode)
        if added == 0:
            return f"Не загружено ни одной таблицы. Ошибки: {errs}"
        tables = [t for t, ref in eng.tables.items() if ref.connector_name == name]
        return (
            f"✅ Подключение «{name}» ({db_type}, mode={mode}) активно!\n"
            f"Загружено таблиц: {added}\n"
            f"Таблицы: {', '.join(tables[:20])}"
            + (f"\nОшибки: {errs}" if errs else "")
        )
    except Exception as e:
        return f"Ошибка подключения: {e}"


@mcp.tool()
async def refresh_schema(connection: str = "") -> str:
    """Обновить схему подключений — перечитать таблицы, колонки, FK из source DB (A3).
    Если connection не указан — обновляет все подключения.
    Полезно когда в БД добавили таблицы/колонки после старта сервера.
    """
    eng = _get_engine()
    added, errs = eng.refresh_connector(connection)
    total = len(eng.tables)
    return (
        f"✅ Схема обновлена!\n"
        f"Таблиц: {added} (всего {total})\n"
        + (f"Ошибки: {errs}" if errs else "")
    )


@mcp.tool()
async def semantic_search(
    table_name: str,
    text_column: str,
    query: str,
    top_k: int = 10,
    where: str = "",
) -> str:
    """Семантический поиск по текстовой колонке через LLM embeddings (C3).
    Находит строки, похожие по смыслу на query, даже если слова не совпадают.
    Требует LLM_BASE_URL/LLM_MODEL (OpenAI-compatible /v1/embeddings).
    """
    eng = _get_engine()
    _resolve_table_for_duckdb(table_name, columns=text_column, where=where, limit=settings.semantic_search_max_rows)

    from .embeddings import semantic_search as _sem_search
    return await _sem_search(eng.session, table_name, text_column, query, top_k, where)


@mcp.tool()
async def test_connection(name: str) -> str:
    """Проверить доступность подключения к БД."""
    eng = _get_engine()
    connector = eng.get_connector_by_name(name)
    if connector is None:
        return f"Подключение '{name}' не найдено. Доступные: {list(eng.connectors.keys())}"
    ok = connector.test()
    return f"✅ Подключение '{name}' работает!" if ok else f"❌ Подключение '{name}' недоступно"

# ───────────────────────────────────────────────
# Аналитические инструменты (переносятся из DataSearcher)
# ───────────────────────────────────────────────

@mcp.tool()
async def profile_data(table_name: str, columns: str = "") -> str:
    """Профилирование: статистика по колонкам (null%, уникальность, min/max, top-5)."""
    _resolve_table_for_duckdb(table_name)
    return await _run("profile_data", table_name=table_name, columns=columns)

@mcp.tool()
async def smart_summary(table_name: str, focus: str = "") -> str:
    """Умное саммари: ключевые метрики, топ-группы, аномалии, паттерны."""
    _resolve_table_for_duckdb(table_name)
    return await _run("smart_summary", table_name=table_name, focus=focus)

@mcp.tool()
async def data_quality_report(table_name: str, key_columns: str = "") -> str:
    """Комплексный отчёт о качестве: полнота, дубликаты, консистентность."""
    _resolve_table_for_duckdb(table_name)
    return await _run("data_quality_report", table_name=table_name, key_columns=key_columns)

@mcp.tool()
async def find_duplicates(
    table_name: str, columns: str = "",
    mode: Literal["exact", "fuzzy"] = "exact", fuzzy_threshold: float = 0.8,
) -> str:
    """Поиск дубликатов: точные или fuzzy (Levenshtein)."""
    _resolve_table_for_duckdb(table_name)
    return await _run("find_duplicates", table_name=table_name, columns=columns,
                      mode=mode, fuzzy_threshold=fuzzy_threshold)

@mcp.tool()
async def detect_anomalies(
    table_name: str, columns: str = "",
    method: Literal["zscore", "iqr", "both"] = "both", threshold: float = 0.0,
) -> str:
    """Обнаружение выбросов z-score и/или IQR."""
    _resolve_table_for_duckdb(table_name)
    return await _run("detect_anomalies", table_name=table_name, columns=columns,
                      method=method, threshold=threshold)

@mcp.tool()
async def sample_data(
    table_name: str, n: int = 10, where: str = "",
    method: Literal["random", "first", "last", "stratified"] = "random",
    stratify_column: str = "",
) -> str:
    """Выборка строк из таблицы."""
    _resolve_table_for_duckdb(table_name)
    return await _run("sample_data", table_name=table_name, n=n, where=where,
                      method=method, stratify_column=stratify_column)

@mcp.tool()
async def correlation_analysis(
    table_name: str, columns: str = "",
    method: Literal["pearson", "spearman"] = "pearson", min_strength: float = 0.3,
) -> str:
    """Корреляционный анализ (Пирсон/Спирмен)."""
    _resolve_table_for_duckdb(table_name, columns=columns)
    return await _run("correlation_analysis", table_name=table_name, columns=columns,
                      method=method, min_strength=min_strength)

@mcp.tool()
async def distribution_analysis(table_name: str, columns: str = "", bins: int = 10) -> str:
    """Анализ распределения: гистограмма, skewness, kurtosis."""
    _resolve_table_for_duckdb(table_name, columns=columns)
    return await _run("distribution_analysis", table_name=table_name, columns=columns, bins=bins)

@mcp.tool()
async def cross_tab(
    table_name: str, row_column: str, col_column: str,
    value_column: str = "",
    agg_function: Literal["count", "sum", "avg", "min", "max"] = "count",
    show_percent: bool = True,
) -> str:
    """Кросс-табуляция двух категорий: частоты, проценты, Хи-квадрат."""
    _resolve_table_for_duckdb(table_name)
    return await _run("cross_tab", table_name=table_name, row_column=row_column,
                      col_column=col_column, value_column=value_column,
                      agg_function=agg_function, show_percent=show_percent)

@mcp.tool()
async def pivot_table(
    table_name: str, row_columns: str, col_column: str, value_column: str,
    agg_function: Literal["sum", "avg", "count", "min", "max"] = "sum",
) -> str:
    """Сводная таблица в стиле Excel (PIVOT)."""
    _resolve_table_for_duckdb(table_name)
    return await _run("pivot_table", table_name=table_name, row_columns=row_columns,
                      col_column=col_column, value_column=value_column,
                      agg_function=agg_function)

@mcp.tool()
async def segment_data(
    table_name: str, column: str,
    method: Literal["quintile", "decile", "quartile", "tertile", "custom"] = "quintile",
    custom_bounds: str = "", rfm_mode: bool = False,
    date_column: str = "", id_column: str = "", amount_column: str = "",
) -> str:
    """Сегментация: квинтили/децилы/кастомные бакеты или RFM-анализ."""
    _resolve_table_for_duckdb(table_name, columns=column)
    return await _run("segment_data", table_name=table_name, column=column, method=method,
                      custom_bounds=custom_bounds, rfm_mode=rfm_mode,
                      date_column=date_column, id_column=id_column, amount_column=amount_column)

@mcp.tool()
async def compare_tables(
    table_a: str, table_b: str, key_columns: str,
    compare_columns: str = "",
    mode: Literal["full", "missing_only", "differences_only"] = "full",
) -> str:
    """Сравнение двух таблиц: общие/уникальные строки, расхождения."""
    _resolve_table_for_duckdb(table_a)
    _resolve_table_for_duckdb(table_b)
    return await _run("compare_tables", table_a=table_a, table_b=table_b,
                      key_columns=key_columns, compare_columns=compare_columns, mode=mode)

@mcp.tool()
async def time_analysis(
    table_name: str, date_column: str = "", value_column: str = "",
    period: Literal["day", "week", "month", "quarter", "year"] = "month",
    moving_avg_window: int = 3,
) -> str:
    """Анализ временных рядов: тренд, рост/падение, скользящее среднее."""
    _resolve_table_for_duckdb(table_name)
    return await _run("time_analysis", table_name=table_name, date_column=date_column,
                      value_column=value_column, period=period, moving_avg_window=moving_avg_window)

@mcp.tool()
async def auto_insights(table_name: str, focus: str = "") -> str:
    """Авто-инсайты: топ-5 находок с графиками одним вызовом."""
    _resolve_table_for_duckdb(table_name)
    return await _run("auto_insights", table_name=table_name, focus=focus)

@mcp.tool()
async def generate_sql(table_name: str, description: str, execute: bool = True) -> str:
    """Генерация DuckDB SQL из описания на естественном языке (требует LLM)."""
    _resolve_table_for_duckdb(table_name)
    return await _run("generate_sql", table_name=table_name, description=description, execute=execute)

@mcp.tool()
async def visualize_data(
    table_name: str,
    chart_type: Literal["bar", "line", "pie", "scatter", "area", "histogram"],
    title: str, x_column: str, y_columns: str,
    sql: str = "", limit: int = 50,
) -> str:
    """Визуализация: bar/line/pie/scatter/area/histogram. PNG + JSON spec."""
    _resolve_table_for_duckdb(table_name)
    return await _run("visualize_data", table_name=table_name, chart_type=chart_type,
                      title=title, x_column=x_column, y_columns=y_columns,
                      sql=sql, limit=limit)

@mcp.tool()
async def predict_trend(
    table_name: str, date_column: str, value_column: str,
    period: Literal["day", "week", "month", "year"] = "month",
    forecast_periods: int = 6,
    model_type: Literal["linear", "polynomial"] = "linear",
    polynomial_degree: int = 2,
) -> str:
    """Прогнозирование тренда (линейная/полиномиальная регрессия)."""
    _resolve_table_for_duckdb(table_name, columns=f"{date_column},{value_column}")
    return await _run("predict_trend", table_name=table_name, date_column=date_column,
                      value_column=value_column, period=period, forecast_periods=forecast_periods,
                      model_type=model_type, polynomial_degree=polynomial_degree)

@mcp.tool()
async def cluster_analysis(
    table_name: str, columns: str,
    method: Literal["kmeans", "dbscan"] = "kmeans",
    n_clusters: int = 0, min_cluster_size: int = 5, sample_size: int = 5000,
) -> str:
    """Кластеризация K-Means/DBSCAN с auto-выбором k (elbow)."""
    _resolve_table_for_duckdb(table_name, columns=columns, limit=sample_size)
    return await _run("cluster_analysis", table_name=table_name, columns=columns,
                      method=method, n_clusters=n_clusters,
                      min_cluster_size=min_cluster_size, sample_size=sample_size)

@mcp.tool()
async def feature_importance(
    table_name: str, target_column: str,
    feature_columns: str = "",
    method: Literal["forest", "permutation", "both"] = "both",
    sample_size: int = 5000,
) -> str:
    """Важность признаков (Random Forest + permutation)."""
    cols = feature_columns or target_column
    _resolve_table_for_duckdb(table_name, columns=cols, limit=sample_size)
    return await _run("feature_importance", table_name=table_name,
                      target_column=target_column, feature_columns=feature_columns,
                      method=method, sample_size=sample_size)

@mcp.tool()
async def statistical_test(
    table_name: str, test: Literal["ttest", "mannwhitney", "ks", "chi2"],
    column: str = "", group_column: str = "",
    group_a: str = "", group_b: str = "",
) -> str:
    """Статистические тесты: t-test, Mann-Whitney, KS, Хи-квадрат."""
    _resolve_table_for_duckdb(table_name)
    return await _run("statistical_test", table_name=table_name, test=test,
                      column=column, group_column=group_column,
                      group_a=group_a, group_b=group_b)

@mcp.tool()
async def classify_rows(
    table_name: str, columns: str, categories: str,
    instruction: str = "", where: str = "", limit: int = 200,
) -> str:
    """Классификация строк по категориям с помощью LLM."""
    _resolve_table_for_duckdb(table_name, columns=columns, where=where, limit=limit)
    return await _run("classify_rows", table_name=table_name, columns=columns,
                      categories=categories, instruction=instruction, where=where, limit=limit)

@mcp.tool()
async def transform_data(
    table_name: str, operations: str, output_table: str = "",
) -> str:
    """Трансформации: normalize, fillna, extract(даты), onehot, bin, derive."""
    _resolve_table_for_duckdb(table_name)
    return await _run("transform_data", table_name=table_name, operations=operations,
                      output_table=output_table)

@mcp.tool()
async def merge_tables(
    table_a: str, table_b: str,
    join_type: Literal["inner", "left", "right", "full"] = "inner",
    key_columns: str = "", output_table: str = "",
) -> str:
    """Умный JOIN двух таблиц с авто-детекцией ключей."""
    _resolve_table_for_duckdb(table_a)
    _resolve_table_for_duckdb(table_b)
    return await _run("merge_tables", table_a=table_a, table_b=table_b,
                      join_type=join_type, key_columns=key_columns,
                      output_table=output_table)

@mcp.tool()
async def export_data(
    table_name: str, sql: str = "", columns: str = "", filename: str = "",
) -> str:
    """Экспорт данных в CSV-файл."""
    _resolve_table_for_duckdb(table_name)
    return await _run("export_data", table_name=table_name, sql=sql,
                      columns=columns, filename=filename)

@mcp.tool()
async def detect_patterns(table_name: str, columns: str = "") -> str:
    """Распознавание паттернов в тексте: email, телефон, URL, ИНН, даты."""
    _resolve_table_for_duckdb(table_name)
    return await _run("detect_patterns", table_name=table_name, columns=columns)

@mcp.tool()
async def build_dashboard(table_name: str, focus: str = "") -> str:
    """Набор из 4-6 ключевых графиков одним вызовом."""
    _resolve_table_for_duckdb(table_name)
    return await _run("build_dashboard", table_name=table_name, focus=focus)

@mcp.tool()
async def data_story(table_name: str, theme: str = "") -> str:
    """Data Story: нарратив с графиками — связный рассказ о данных."""
    _resolve_table_for_duckdb(table_name)
    return await _run("data_story", table_name=table_name, theme=theme)

@mcp.tool()
async def create_public_dashboard(title: str, description: str = "") -> str:
    """Создаёт дашборд — standalone HTML с интерактивными фильтрами."""
    return await _run("create_public_dashboard", title=title, description=description)

@mcp.tool()
async def load_file(path: str, table_name: str = "", sheet: str = "") -> str:
    """Загрузка CSV/Excel/Parquet файла в DuckDB для анализа.
    Excel: если sheet не указан, грузит все листы. Parquet загружается через DuckDB read_parquet.
    """
    eng = _get_engine()
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    if ext == "parquet":
        fi = eng.load_parquet(path, table_name)
    elif ext in ("xlsx", "xls"):
        fis = eng.load_excel(path, table_name, sheet)
        fi = fis[0] if fis else None
        if fis and len(fis) > 1:
            names = [f.table_name for f in fis]
            return f"✅ Загружено листов: {len(fis)}\nТаблицы: {', '.join(names)}"
    else:
        fi = eng.load_csv(path, table_name)
    if fi:
        return f"✅ Загружена таблица `{fi.table_name}` ({fi.row_count:,} строк, {len(fi.columns)} колонок)"
    return f"Ошибка загрузки: {eng.errors()[-1] if eng.errors() else 'неизвестно'}"


# ───────────────────────────────────────────────
# Knowledge Base tools (ТЗ 1.1, v1)
# ───────────────────────────────────────────────

@mcp.tool()
async def update_metadata(
    table_name: str,
    description: str = "",
    owner: str = "",
    layer: str = "",
    is_certified: bool = False,
    column_descriptions: str = "",
) -> str:
    """Обновить метаописание таблицы в Knowledge Base (ТЗ 1.1).
    column_descriptions: JSON {\"col1\": \"описание\", \"col2\": \"...\"}
    layer: raw | staging | mart | certified
    """
    from .knowledge_base import get_kb

    kb = get_kb()
    kb.upsert_table(
        table_name=table_name,
        description=description or None,
        owner=owner or None,
        layer=layer or None,
        is_certified=is_certified or None,
        source="manual",
    )

    if column_descriptions:
        try:
            cols = json.loads(column_descriptions)
            for col_name, col_desc in cols.items():
                kb.upsert_column(table_name, col_name, description=col_desc, source="manual")
        except json.JSONDecodeError:
            pass

    from .logging_db import get_log_db
    get_log_db().log_audit("update_metadata", table_name, {"description": description[:100]})
    return f"✅ Метаописание таблицы '{table_name}' обновлено."


@mcp.tool()
async def list_metrics() -> str:
    """Список расчётных метрик с формулами из Knowledge Base (ТЗ 1.1)."""
    from .knowledge_base import get_kb
    from .tools.registry import format_table

    metrics = get_kb().all_metrics()
    if not metrics:
        return "Метрики не заданы. Используйте update_metadata для добавления формул."
    rows = [(m["name"], m["formula"][:60], m["description"][:60], m["owner"]) for m in metrics]
    return format_table(["Метрика", "Формула", "Описание", "Владелец"], rows)


@mcp.tool()
async def scan_pii(table_name: str) -> str:
    """Сканировать таблицу на PII и пометить чувствительные колонки (ТЗ 10)."""
    from .pii_detector import scan_table_for_pii, _PII_PATTERNS

    eng = _get_engine()
    _resolve_table_for_duckdb(table_name, limit=settings.pii_scan_rows)

    try:
        result = eng.session.conn.execute(f'SELECT * FROM "{table_name}" LIMIT {settings.pii_scan_rows}')
        cols = [{"name": d[0], "type": str(d[1])} for d in result.description]
        rows = result.fetchall()
    except Exception as e:
        return f"Ошибка: {e}"

    found = scan_table_for_pii(table_name, cols, rows)
    if found:
        lines = [f"Найдено PII в таблице {table_name}:"]
        for f in found:
            lines.append(f"  - {f['column']}: {f['pii_type']}")
        return "\n".join(lines)
    return f"PII в таблице {table_name} не обнаружено."


@mcp.tool()
async def get_logs(log_type: Literal["query", "error", "audit"] = "query", limit: int = 20) -> str:
    """Получить логи запросов/ошибок/аудита (ТЗ 9)."""
    from .logging_db import get_log_db
    from .tools.registry import format_table

    log_db = get_log_db()
    if log_type == "query":
        logs = log_db.get_query_logs(limit)
        if not logs:
            return "Логи запросов пусты."
        rows = [(l["timestamp"][:19], l["tool"], l.get("table_name", ""), str(l["duration_ms"]) + "ms",
                 "✅" if l["success"] else "❌") for l in logs]
        return format_table(["Время", "Инструмент", "Таблица", "Длительность", "Статус"], rows)
    elif log_type == "error":
        logs = log_db.get_error_logs(limit)
        if not logs:
            return "Логи ошибок пусты."
        rows = [(l["timestamp"][:19], l["error_type"], l["message"][:50]) for l in logs]
        return format_table(["Время", "Тип", "Сообщение"], rows)
    else:
        logs = log_db.get_audit_logs(limit)
        if not logs:
            return "Аудит-лог пуст."
        rows = [(l["timestamp"][:19], l["action"], l["target"]) for l in logs]
        return format_table(["Время", "Действие", "Объект"], rows)


# ───────────────────────────────────────────────
# dbt tools (ТЗ 1.2, v1.5)
# ───────────────────────────────────────────────

@mcp.tool()
async def load_dbt(manifest_path: str = "") -> str:
    """Загрузить метаданные из dbt manifest.json в Knowledge Base (ТЗ 1.2)."""
    from .dbt_loader import load_dbt_manifest
    from .config import settings as cfg

    path = manifest_path or cfg.dbt_manifest_path
    if not path:
        return "Укажите manifest_path или задайте dbt_manifest_path в конфиге."
    result = load_dbt_manifest(path)
    if result.get("error"):
        return f"❌ {result['error']}"
    return (f"✅ dbt manifest загружен!\n"
            f"Моделей: {result.get('models', 0)}, Источников: {result.get('sources', 0)}, "
            f"Колонок: {result.get('columns', 0)}, Тестов: {result.get('tests', 0)}")


# ───────────────────────────────────────────────
# XLSX export (ТЗ 3.3, v1.5)
# ───────────────────────────────────────────────

@mcp.tool()
async def export_xlsx(
    table_name: str,
    sql: str = "",
    columns: str = "",
    filename: str = "",
) -> str:
    """Экспорт данных в XLSX-файл с форматированием (ТЗ 3.3).
    Заголовки жирным, freeze panes, автоширина, автофильтр, NULL → серый фон.
    """
    from .tools.export_xlsx import export_to_xlsx

    eng = _get_engine()
    _resolve_table_for_duckdb(table_name)
    result = export_to_xlsx(eng.session, table_name, sql=sql, columns=columns, filename=filename)
    return await _postprocess(result, "export_xlsx")


# ───────────────────────────────────────────────
# Example Store + Search (ТЗ 1.3, 8, v2)
# ───────────────────────────────────────────────

@mcp.tool()
async def add_example(query: str, sql: str, table_name: str = "", is_golden: bool = False) -> str:
    """Добавить эталонный пример «NL-запрос → SQL» в Example Store (ТЗ 1.3).
    Используется для few-shot обучения generate_sql.
    """
    from .example_store import get_example_store
    ex_id = get_example_store().add_example(query, sql, table_name, success=True, is_golden=is_golden)
    return f"✅ Пример #{ex_id} добавлен в Example Store."


@mcp.tool()
async def search_knowledge(query: str, top_k: int = 5) -> str:
    """Поиск по базе знаний: метаданные таблиц, описания колонок, метрики, примеры (ТЗ 8).
    Комбинирует полнотекстовый и семантический поиск.
    """
    from .knowledge_base import get_kb
    from .tools.registry import format_table

    # 1. Полнотекстовый поиск по KB
    kb_results = get_kb().search(query, limit=top_k)

    # 2. Семантический поиск по Example Store
    examples = []
    try:
        from .example_store import get_example_store
        from .config import settings as cfg
        if cfg.example_store_enabled:
            store = get_example_store()
            examples = await store.async_search_similar(query, top_k=3)
    except Exception:
        pass

    out = [f"# Поиск по базе знаний: '{query}'\n"]

    if kb_results:
        out.append("## Метаданные\n")
        rows = []
        for r in kb_results:
            rtype = r.get("type", "")
            if rtype == "table":
                rows.append((r.get("table_name", ""), "таблица", r.get("description", "")[:50], r.get("owner", "")))
            elif rtype == "column":
                rows.append((f"{r.get('table_name','')}.{r.get('column_name','')}", "колонка", r.get("description", "")[:50], ""))
            elif rtype == "metric":
                rows.append((r.get("name", ""), "метрика", r.get("description", "")[:50], r.get("formula", "")[:40]))
        if rows:
            out.append(format_table(["Объект", "Тип", "Описание", "Доп."], rows))

    if examples:
        out.append("\n## Похожие примеры запросов\n")
        rows = []
        for ex in examples:
            rows.append((ex.get("query", "")[:80], ex.get("sql", "")[:80], "⭐" if ex.get("is_golden") else ""))
        out.append(format_table(["Запрос", "SQL", "Эталон"], rows))

    if not kb_results and not examples:
        out.append("Ничего не найдено. Попробуйте другой запрос.")

    return "\n".join(out)


# ───────────────────────────────────────────────
# DataHub (ТЗ 1.2, v2)
# ───────────────────────────────────────────────

@mcp.tool()
async def sync_datahub() -> str:
    """Синхронизировать метаданные из DataHub в Knowledge Base (ТЗ 1.2)."""
    from .datahub_client import DataHubClient

    client = DataHubClient()
    if not client.enabled:
        return "DataHub не настроен. Задайте datahub_url и datahub_token в конфиге."
    result = client.sync_datasets()
    if result.get("error"):
        return f"❌ {result['error']}"
    return f"✅ Синхронизировано из DataHub: {result.get('synced', 0)} датасетов."


# ───────────────────────────────────────────────
# BI link builder (ТЗ 3.4, v3)
# ───────────────────────────────────────────────

@mcp.tool()
async def build_bi_link(
    tool: Literal["superset", "grafana", "datalens", "tableau", "powerbi"],
    base_url: str,
    dashboard_id: str = "",
    params: str = "",
    time_from: str = "",
    time_to: str = "",
) -> str:
    """Сгенерировать URL для внешнего BI-инструмента с предзаполненными фильтрами (ТЗ 3.4).
    params: JSON {\"region\": \"Москва\", \"product\": \"Widget A\"}
    time_from/time_to: для Grafana (например '2024-01-01', '2024-02-01')
    """
    from .bi_linker import build_bi_link as _build

    params_dict = {}
    if params:
        try:
            params_dict = json.loads(params)
        except json.JSONDecodeError:
            return f"❌ params должен быть JSON, например: {{\"region\": \"Москва\"}}"

    time_range = None
    if time_from and time_to:
        time_range = (time_from, time_to)

    url = _build(tool, base_url, dashboard_id, params_dict, time_range)
    return f"🔗 {tool.capitalize()} URL:\n\n{url}\n\nОткройте в браузере."


# ───────────────────────────────────────────────
# Ресурсы
# ───────────────────────────────────────────────

@mcp.resource("schema://tables")
def list_tables_resource() -> str:
    """Список всех таблиц с колонками, типами и бизнес-описаниями из KB (ТЗ 1.1)."""
    from .knowledge_base import get_kb

    eng = _get_engine()
    tables = eng.tables_summary()
    if not tables:
        return "Нет загруженных таблиц. Настройте connections.yaml или используйте load_file."
    kb = get_kb()
    out = ["# Доступные таблицы\n"]
    for t in tables:
        status = "🟢 DuckDB" if t["in_duckdb"] else "🔵 remote"
        # KB enrichment
        kb_meta = kb.get_table(t["table_name"])
        if kb_meta:
            if kb_meta.get("is_certified"):
                status += " ✅ certified"
            if kb_meta.get("layer"):
                status += f" [{kb_meta['layer']}]"
            if kb_meta.get("owner"):
                status += f" 👤 {kb_meta['owner']}"

        out.append(f"## {t['table_name']} ({t['row_count']:,} строк, {t['file_type']}) {status}")
        out.append(f"Источник: `{t['source']}`")

        if kb_meta and kb_meta.get("description"):
            out.append(f"📝 {kb_meta['description']}")

        # PII marks
        pii_cols = kb.get_pii_columns(t["table_name"])
        pii_names = {p["column_name"] for p in pii_cols}

        out.append("\n| Колонка | Тип | Описание | PII |")
        out.append("|---|---|---|---|")
        for c in t["columns"]:
            cn = c["name"]
            col_meta = kb.get_column(t["table_name"], cn)
            desc = col_meta.get("description", "") if col_meta else ""
            pii_mark = "🔒 " + (col_meta.get("pii_type", "") if col_meta else "") if cn in pii_names else ""
            out.append(f"| {cn} | {c['type']} | {desc} | {pii_mark} |")
        out.append("")
    return "\n".join(out)

@mcp.resource("connection://list")
def list_connections_resource() -> str:
    """Подключения к БД."""
    eng = _get_engine()
    if not eng.connection_configs:
        return "Нет активных подключений. Настройте connections.yaml или используйте attach_database."
    out = ["# Подключения\n"]
    for c in eng.connection_configs:
        out.append(f"- **{c['name']}** ({c['db_type']}, mode={c.get('mode','auto')}): {c['tables_loaded']} таблиц")
    errs = eng.errors()
    if errs:
        out.append("\n## Ошибки загрузки\n")
        for e in errs:
            out.append(f"- {e}")
    return "\n".join(out)

@mcp.resource("table://{table_name}/preview")
def preview_table_resource(table_name: str) -> str:
    """Превью строк таблицы (первые 5 строк)."""
    eng = _get_engine()
    try:
        _resolve_table_for_duckdb(table_name, limit=5)
        result = eng.session.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 5')
        cols = [d[0] for d in result.description]
        rows = result.fetchall()
        from .tools.registry import format_table
        return f"Превью {table_name}:\n\n" + format_table(cols, rows)
    except Exception as e:
        return f"Ошибка: {e}"


@mcp.resource("schema://diagram")
def er_diagram_resource() -> str:
    """Mermaid ER-диаграмма таблиц и связей (D5). FK + эвристика по именам.
    Рендерится в чате Claude/Cursor как визуальная диаграмма.
    """
    eng = _get_engine()
    if not eng.tables:
        return "Нет таблиц для диаграммы."

    lines = ["# ER-диаграмма\n", "```mermaid", "erDiagram"]

    # Описания таблиц
    for tname, ref in eng.tables.items():
        col_lines = []
        for c in ref.columns[:15]:  # лимит колонок для читаемости
            cn = c["name"]
            ct = c.get("type", "VARCHAR").upper()
            # Mermaid типы: int, string, real, text, date
            if "INT" in ct:
                mt = "int"
            elif any(x in ct for x in ("FLOAT", "DOUBLE", "DECIMAL", "REAL")):
                mt = "real"
            elif "DATE" in ct or "TIME" in ct:
                mt = "date"
            elif "TEXT" in ct or "VARCHAR" in ct or "CHAR" in ct:
                mt = "string"
            else:
                mt = "string"
            is_pk = cn.lower() == "id" or cn.lower() == f"{tname.lower()}_id"
            pk_marker = " PK" if is_pk else ""
            col_lines.append(f"    {mt} {cn}{pk_marker}")
        lines.append(f"  {tname} {{")
        lines.extend(col_lines[:10])
        lines.append("  }")

    # Связи из FK (правильное направление: parent → child)
    fk_graph = eng.fk_graph()
    drawn = set()
    for tname, fks in fk_graph.items():
        for fk in fks:
            ref_table = fk.get("ref_table", "")
            ref_col = fk.get("ref_column", "id")
            col = fk.get("column", "")
            if ref_table and ref_table in {r.name for r in eng.tables.values()}:
                # найти table_name для ref_table (parent)
                ref_tname = next(
                    (t for t, r in eng.tables.items() if r.name == ref_table),
                    ref_table,
                )
                pair = tuple(sorted([tname, ref_tname]))
                if pair not in drawn:
                    drawn.add(pair)
                    # parent ||--o{ child : "fk → ref"
                    lines.append(f"  {ref_tname} ||--o{{ {tname} : \"{col} → {ref_col}\"")

    # Эвристические связи (если FK нет)
    if not drawn:
        table_list = list(eng.tables.items())
        for i, (tname_a, ref_a) in enumerate(table_list):
            for tname_b, ref_b in table_list[i + 1:]:
                keys = eng.find_join_keys(tname_a, tname_b)
                if keys:
                    ka, kb = keys[0]
                    lines.append(f"  {tname_b} ||--o{{ {tname_a} : \"{ka} → {kb}\"")

    lines.append("```")
    return "\n".join(lines)


@mcp.resource("knowledge://tables")
def knowledge_tables_resource() -> str:
    """Бизнес-метаданные: описания таблиц, владельцы, теги, метрики (ТЗ 1.1)."""
    from .knowledge_base import get_kb

    kb = get_kb()
    tables = kb.all_tables()
    metrics = kb.all_metrics()

    out = ["# База знаний\n"]

    if tables:
        out.append("## Таблицы\n")
        for t in tables:
            cert = "✅" if t.get("is_certified") else "📋"
            out.append(f"### {cert} {t['table_name']}")
            if t.get("description"):
                out.append(f"📝 {t['description']}")
            if t.get("owner"):
                out.append(f"👤 Владелец: {t['owner']}")
            if t.get("layer"):
                out.append(f"🏷️ Слой: {t['layer']}")
            tags = t.get("tags", [])
            if tags:
                out.append(f"🔍 Теги: {', '.join(tags)}")

            cols = kb.get_columns(t["table_name"])
            described = [c for c in cols if c.get("description")]
            pii_cols = [c for c in cols if c.get("pii_type")]
            if described:
                out.append("\nКолонки с описаниями:")
                for c in described[:10]:
                    pii = f" 🔒{c['pii_type']}" if c.get("pii_type") else ""
                    out.append(f"  - {c['column_name']}: {c['description'][:60]}{pii}")
            if pii_cols:
                out.append(f"\n🔒 PII колонки: {', '.join(c['column_name'] for c in pii_cols)}")
            out.append("")

    if metrics:
        out.append("## Метрики\n")
        for m in metrics:
            out.append(f"### {m['name']}")
            out.append(f"📝 {m.get('description', '')}")
            out.append(f"📊 `{m.get('formula', '')}`")
            if m.get("owner"):
                out.append(f"👤 {m['owner']}")
            out.append("")

    if not tables and not metrics:
        out.append("База знаний пуста. Используйте:\n"
                   "- `update_metadata` — описать таблицу\n"
                   "- `load_dbt` — импорт из dbt manifest\n"
                   "- `sync_datahub` — синхронизация с DataHub")

    return "\n".join(out)


@mcp.resource("reasoning://last")
def reasoning_resource() -> str:
    """Ход рассуждений последнего запроса — Chain of Thought (ТЗ 4.1)."""
    from .logging_db import get_log_db
    from .tools.registry import format_table

    logs = get_log_db().get_query_logs(limit=10)
    if not logs:
        return "История запросов пуста."

    out = ["# Chain of Thought — последние запросы\n"]
    out.append("| Время | Инструмент | Таблица | Длительность | Статус |")
    out.append("|---|---|---|---|---|")
    for l in logs:
        status = "✅" if l["success"] else "❌"
        err = f" ({l['error'][:40]})" if l.get("error") else ""
        out.append(f"| {l['timestamp'][:19]} | {l['tool']} | {l.get('table_name', '')} | {l['duration_ms']}ms | {status}{err} |")

    out.append("\n💡 Разверните блок рассуждений в чате, чтобы увидеть логику выполнения.")
    return "\n".join(out)

# ───────────────────────────────────────────────
# Промпты
# ───────────────────────────────────────────────
@mcp.prompt()
def analyze_table(table: str = "") -> str:
    """Системный промпт аналитика с контекстом схемы для заданной таблицы."""
    from .prompts.system import build_system_prompt
    eng = _get_engine()
    table_info = [
        {
            "table_name": ref.table_name,
            "file_type": ref.file_type,
            "row_count": ref.row_count,
            "columns": ref.columns,
            "source": ref.source,
            "in_duckdb": ref.in_duckdb,
        }
        for ref in eng.tables.values()
    ]
    if table:
        table_info = [t for t in table_info if t["table_name"] == table] or table_info
    return build_system_prompt(table_info)

@mcp.prompt()
def weekly_report(table: str, date_column: str = "", value_column: str = "") -> str:
    """Шаблон еженедельного отчёта по таблице (фича D).
    Запускает профиль + дашборд + авто-инсайты + экспорт одной командой.
    """
    eng = _get_engine()
    ref = eng.get_table_ref(table)
    if not ref:
        return f"Таблица '{table}' не найдена."
    cols = ", ".join(f"{c['name']} ({c['type']})" for c in ref.columns)
    return f"""Создай еженедельный отчёт по таблице {table}.

Шаги:
1. profile_data для {table} — общая статистика
2. auto_insights для {table} — топ-5 находок
3. time_analysis для {table} (date_column={date_column or 'авто'}, value_column={value_column or 'авто'}) — тренд за неделю
4. visualize_data — график тренда (line)
5. export_data — экспорт результатов в CSV
6. data_story — нарратив с графиками

Колонки: {cols}
Строк: {ref.row_count:,}

Собери всё в единый markdown-отчёт с выводами и рекомендациями."""

