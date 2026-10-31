from __future__ import annotations

import re

from .config import settings

_BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
    "CREATE", "GRANT", "REVOKE", "MERGE", "CALL", "VACUUM",
    "REINDEX", "REFRESH", "ATTACH", "DETACH", "PRAGMA",
    "COPY", "BULK", "LOAD", "IMPORT",
}

_ALLOWED_KEYWORDS = {
    "SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE", "DESC",
    "VALUES",
}


def check_read_only(sql: str) -> tuple[bool, str]:
    """Проверить, что SQL — read-only (SELECT/CTE/EXPLAIN).

    Returns:
        (True, "") если запрос безопасен.
        (False, reason) если нарушает read-only.
    """
    if not settings.read_only:
        return True, ""

    sql_stripped = sql.strip()
    if not sql_stripped:
        return True, ""

    # Извлечь первый statement (до ;)
    first_stmt = sql_stripped.split(";")[0].strip()

    # Первое слово — тип statement
    first_word = first_stmt.split()[0].upper() if first_stmt.split() else ""

    # WITH ... SELECT — ок (CTE)
    if first_word in _ALLOWED_KEYWORDS:
        return True, ""

    # Проверяем блокированные ключевые слова в начале
    if first_word in _BLOCKED_KEYWORDS:
        return False, (
            f"⛔ Read-only режим: запрос типа '{first_word}' заблокирован. "
            f"Разрешены только SELECT/WITH/EXPLAIN/SHOW/DESCRIBE. "
            f"Установите read_only=false в конфиге для полного доступа."
        )

    # Проверка на INSERT/UPDATE/DELETE внутри CTE или подзапроса
    # (WITH ... AS (INSERT ...) — редкий случай)
    upper_sql = sql_stripped.upper()
    for kw in ("INSERT INTO", "UPDATE ", "DELETE FROM", "DROP ", "TRUNCATE ", "ALTER ", "CREATE "):
        if kw in upper_sql:
            return False, (
                f"⛔ Read-only режим: обнаружен оператор изменения данных '{kw.strip()}' в запросе. "
                f"Разрешены только SELECT-запросы."
            )

    return True, ""
