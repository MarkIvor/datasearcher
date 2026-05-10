from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:14b"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1

    max_file_size_mb: int = 100
    session_ttl_minutes: int = 60
    duckdb_memory_limit: str = "2GB"
    upload_dir: str = "/app/uploads"
    max_result_rows: int = 200
    max_preview_rows: int = 5
    max_tool_iterations: int = 15
    classify_batch_size: int = 50

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
