from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── LLM ─────────────────────────────────────
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:14b"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1

    # ── Файлы / сессии / DuckDB ────────────────
    max_file_size_mb: int = 100
    session_ttl_minutes: int = 60
    duckdb_memory_limit: str = "2GB"
    upload_dir: str = "/app/uploads"
    max_result_rows: int = 200
    max_preview_rows: int = 5
    max_tool_iterations: int = 15
    classify_batch_size: int = 50

    # ── Режим подключений по умолчанию ──────────
    # remote  — SQL в source DB (push-down)
    # dump    — таблицы выгружаются в DuckDB
    # auto    — remote для SQL, lazy-dump для ML
    # federated — source DB аттачится к DuckDB
    default_mode: str = "auto"

    # ── Query timeout (сек), 0 = без лимита ────
    query_timeout: int = 60

    # ── sqlglot трансляция SQL-диалектов ────────
    auto_translate: bool = True

    # ── DuckDB extensions (federated) ──────────
    duckdb_extensions: str = "postgres_scanner,mysql_scanner,sqlite_scanner"

    # ── Embeddings (semantic search) ───────────
    embeddings_dir: str = ""
    semantic_search_max_rows: int = 10000

    # ── ML-кеш ─────────────────────────────────
    ml_cache_enabled: bool = True
    ml_cache_max_tables: int = 20

    # ── Директории экспорта/графиков/дашбордов ─
    exports_dir: str = ""
    charts_dir: str = ""
    dashboards_dir: str = ""

    # ── Knowledge Base (SQLite) ─────────────────
    kb_db_path: str = ""  # пусто = ./datasearcher_kb.db

    # ── Read-only guard (блок DML/DDL) ─────────
    read_only: bool = True

    # ── Семантический слой (фильтр таблиц) ─────
    blocked_table_patterns: str = "raw_*,stg_*,tmp_*,_*,test_*"
    certified_only: bool = False

    # ── PII masking ────────────────────────────
    pii_masking: bool = True
    pii_scan_rows: int = 10

    # ── Rate limiting ──────────────────────────
    rate_limit_sql: int = 60
    rate_limit_ml: int = 10
    rate_limit_enabled: bool = True

    # ── Logging (SQLite append-only) ───────────
    log_db_path: str = ""  # пусто = ./datasearcher_logs.db
    log_enabled: bool = True

    # ── CoT / Progress ─────────────────────────
    cot_enabled: bool = True

    # ── dbt manifest ────────────────────────────
    dbt_manifest_path: str = ""

    # ── DataHub ────────────────────────────────
    datahub_url: str = ""
    datahub_token: str = ""

    # ── Example Store (NL→SQL few-shot) ────────
    example_store_enabled: bool = True

    # ── Транспорт ──────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
