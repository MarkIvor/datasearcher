from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Файл конфигурации подключений ───────────
    connections_file: str = "connections.yaml"

    # ── DuckDB ──────────────────────────────────
    # По умолчанию ВЫКЛЮЧЕН: таблицы не выгружаются в DuckDB при старте.
    # DuckDB включается лениво при вызове ML-инструментов (cluster, predict,
    # feature_importance, statistical_test) или при явном запросе через
    # ensure_table / load_csv / load_excel.
    duckdb_enabled: bool = False
    duckdb_memory_limit: str = "2GB"
    duckdb_threads: int = 4
    max_result_rows: int = 200
    max_preview_rows: int = 5
    max_tool_iterations: int = 15
    classify_batch_size: int = 50

    # ── Режим по умолчанию для подключений ──────
    # remote  — SQL выполняется в source DB (push-down), DuckDB не используется
    # dump    — таблицы выгружаются в DuckDB при старте
    # auto    — remote для SQL-инструментов, lazy-dump для ML-инструментов
    # federated — source DB аттачится к DuckDB через расширение (кросс-БД JOIN)
    default_mode: str = "auto"

    # ── Query timeout (B1) ──────────────────────
    # Таймаут remote SQL-запросов в секундах. 0 = без лимита.
    query_timeout: int = 60

    # ── SQL translation (A1) ────────────────────
    # Автоматический перевод DuckDB SQL в диалект source DB через sqlglot.
    auto_translate: bool = True

    # ── DuckDB extensions (A2) ──────────────────
    # Расширения для federated-режима. Устанавливаются лениво.
    duckdb_extensions: str = "postgres_scanner,mysql_scanner,sqlite_scanner"

    # ── Auth для HTTP (B3) ──────────────────────
    # Bearer token для http/sse транспорта. Пусто = без auth.
    auth_token: str = ""

    # ── Embeddings (C3) ─────────────────────────
    # Директория для кеша embeddings. Пусто = tempfile/datasearcher_mcp_embeddings
    embeddings_dir: str = ""
    # Лимит строк для semantic_search
    semantic_search_max_rows: int = 10000

    # ── Кеширование ML-выборок (фича C) ─────────
    ml_cache_enabled: bool = True
    ml_cache_max_tables: int = 20

    # ── Рендеринг графиков ──────────────────────
    # json — только chart-spec JSON в тексте
    # png  — рендер в PNG (matplotlib)
    # both — JSON + PNG (по умолчанию)
    charts_mode: str = "both"
    charts_dir: str = ""

    # ── Экспорт ─────────────────────────────────
    exports_dir: str = ""

    # ── Дашборды ────────────────────────────────
    dashboards_dir: str = ""

    # ── LLM (для classify_rows / generate_sql) ──
    # builtin — использовать llm_* настройки (OpenAI-compatible API)
    # sampling — использовать MCP sampling (модель хоста: Claude/Cursor)
    # none — инструменты возвращают инструкцию для хоста
    llm_mode: str = "builtin"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1

    # ── Транспорт ───────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Knowledge Base (ТЗ 1.1) ────────────────
    # SQLite-файл с метаописаниями: бизнес-описания, владельцы, формулы метрик
    kb_db_path: str = ""  # пусто = ./datasearcher_mcp_kb.db

    # ── Read-only guard (ТЗ 2.1, 10) ───────────
    # Блокировка DML/DDL в sql_query (INSERT/UPDATE/DELETE/DROP и т.д.)
    read_only: bool = True

    # ── Семантический слой (ТЗ 2.2) ─────────────
    # Фильтрация raw/staging таблиц. Паттерны исключений (glob).
    blocked_table_patterns: str = "raw_*,stg_*,tmp_*,_*,test_*"
    certified_only: bool = False

    # ── PII masking (ТЗ 10) ────────────────────
    pii_masking: bool = True
    # Сколько строк сканировать при авто-детекции PII
    pii_scan_rows: int = 10

    # ── Rate limiting (ТЗ 11) ───────────────────
    rate_limit_sql: int = 60       # SQL-запросов в минуту
    rate_limit_ml: int = 10        # ML-инструментов в минуту
    rate_limit_enabled: bool = True

    # ── Logging (ТЗ 9) ──────────────────────────
    log_db_path: str = ""  # пусто = ./datasearcher_mcp_logs.db
    log_enabled: bool = True

    # ── CoT / Progress (ТЗ 4.1) ─────────────────
    cot_enabled: bool = True

    # ── dbt (ТЗ 1.2, v1.5) ──────────────────────
    dbt_manifest_path: str = ""

    # ── DataHub (ТЗ 1.2, v2) ────────────────────
    datahub_url: str = ""
    datahub_token: str = ""

    # ── Example Store (ТЗ 1.3, v2) ──────────────
    example_store_enabled: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "datasearcher_mcp_",
        "extra": "ignore",
    }


settings = Settings()
