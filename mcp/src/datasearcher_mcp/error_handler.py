from __future__ import annotations

import re
from typing import Any


_ERROR_PATTERNS: list[tuple[str, str, str]] = [
    # (pattern, error_type, human_message_template)
    (r"syntax error|parse error|unexpected",
     "Синтаксическая ошибка SQL",
     "Синтаксическая ошибка SQL. Проверьте правильность: {detail}"),
    (r"permission denied|access denied|unauthorized|insufficient",
     "Нет прав доступа",
     "Нет прав доступа к таблице/колонке. Обратитесь к владельцу данных."),
    (r"relation.*does not exist|table.*not found|unknown table",
     "Таблица не найдена",
     "Таблица не найдена: {detail}. Используйте schema://tables для списка доступных таблиц."),
    (r"column.*does not exist|column.*not found|unknown column|unresolved.*column",
     "Колонка не найдена",
     "Колонка не найдена: {detail}. Проверьте названия колонок через get_schema."),
    (r"timeout|timed out|query.*exceeded|max.*execution",
     "Таймаут запроса",
     "Превышен таймаут запроса. Упростите запрос, добавьте фильтр WHERE, "
     "или увеличьте query_timeout в конфиге."),
    (r"connection.*refused|connection.*failed|could not connect|server closed",
     "БД недоступна",
     "База данных недоступна. Проверьте подключение и доступность сервера."),
    (r"duplicate|unique constraint|already exists",
     "Конфликт данных",
     "Конфликт уникальности: {detail}."),
    (r"type.*does not exist|invalid input syntax|cast.*failed",
     "Ошибка типа данных",
     "Ошибка типа данных: {detail}. Проверьте, что колонки имеют правильный тип."),
    (r"transaction.*aborted|deadlock",
     "Транзакция прервана",
     "Транзакция прервана: {detail}."),
    (r"out of memory|resource.*exhausted",
     "Недостаточно ресурсов",
     "Недостаточно ресурсов БД. Уменьшите объём данных или добавьте лимиты LIMIT."),
]


def explain_error(exc: Exception, context: str = "") -> dict:
    """Преобразовать SQL-ошибку в человекочитаемое сообщение.

    Returns:
        {error_type, message, detail, suggestion}
    """
    raw_msg = str(exc)
    msg_lower = raw_msg.lower()

    for pattern, error_type, template in _ERROR_PATTERNS:
        if re.search(pattern, msg_lower):
            detail = raw_msg.split("\n")[0][:200]
            message = template.format(detail=detail) if "{detail}" in template else template
            return {
                "error_type": error_type,
                "message": message,
                "detail": detail,
                "suggestion": _get_suggestions(error_type, context),
            }

    # Неизвестная ошибка
    detail = raw_msg.split("\n")[0][:300]
    return {
        "error_type": "Неизвестная ошибка",
        "message": f"Ошибка при выполнении запроса: {detail}",
        "detail": detail,
        "suggestion": "Проверьте синтаксис SQL и доступность таблиц/колонок.",
    }


def _get_suggestions(error_type: str, context: str) -> str:
    suggestions = {
        "Синтаксическая ошибка SQL": "Проверьте синтаксис DuckDB SQL. Используйте sqlglot-совместимый синтаксис.",
        "Нет прав доступа": "Узнайте владельца данных через schema://tables и запросите права.",
        "Таблица не найдена": "Вызовите schema://tables для списка доступных таблиц.",
        "Колонка не найдена": "Вызовите get_schema(table_name) для списка колонок.",
        "Таймаут запроса": "Добавьте WHERE-фильтр, LIMIT, или используйте query_explain для оптимизации.",
        "БД недоступна": "Проверьте test_connection(name). Возможно БД перезапускается.",
        "Ошибка типа данных": "Используйте CAST(column AS type) для преобразования типов.",
    }
    return suggestions.get(error_type, "Проверьте запрос и доступность данных.")


def format_error_response(exc: Exception, context: str = "") -> str:
    """Форматировать ошибку для возврата в MCP (markdown)."""
    info = explain_error(exc, context)
    lines = [
        f"❌ **{info['error_type']}**",
        "",
        info["message"],
        "",
        f"💡 **Подсказка:** {info['suggestion']}",
    ]
    if info["detail"]:
        lines.append(f"\n`{info['detail']}`")
    return "\n".join(lines)
