from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="attach_database",
    description="Подключить новую базу данных в рантайме (PostgreSQL, MySQL, ClickHouse, SQLite). После подключения таблицы доступны для анализа.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Имя подключения (произвольное)"},
            "db_type": {"type": "string", "description": "Тип БД: postgresql | mysql | clickhouse | sqlite"},
            "host": {"type": "string", "description": "Хост"},
            "port": {"type": "integer", "description": "Порт"},
            "database": {"type": "string", "description": "Имя БД / путь к файлу для sqlite"},
            "username": {"type": "string", "description": "Пользователь"},
            "password": {"type": "string", "description": "Пароль"},
            "mode": {"type": "string", "description": "Режим: auto | remote | dump | federated"},
        },
        "required": ["name", "db_type"],
    },
)
def attach_database(
    session: Session,
    name: str,
    db_type: str,
    host: str = "",
    port: int = 0,
    database: str = "",
    username: str = "",
    password: str = "",
    mode: str = "auto",
) -> str:
    from ..engine import get_engine_for_session
    eng = get_engine_for_session(session)

    params = {
        "host": host, "port": port, "database": database,
        "username": username, "password": password,
    }
    if db_type == "sqlite":
        params = {"database": database}

    added, errors = eng.attach_connector(name, db_type, params, mode=mode)
    table_names = sorted(eng.tables.keys())[:20]
    out = [
        f"✅ Подключение '{name}' ({db_type}, режим {mode}) активно.",
        f"Загружено таблиц: {added}",
    ]
    if table_names:
        out.append("")
        out.append("Доступные таблицы:")
        for t in table_names:
            out.append(f"  - {t}")
    if errors:
        out.append("")
        out.append("Ошибки:")
        for e in errors[:10]:
            out.append(f"  - {e}")
    return "\n".join(out)