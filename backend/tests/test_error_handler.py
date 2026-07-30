from __future__ import annotations

from app.services.error_handler import explain_error, format_error_response, _get_suggestions


class TestExplainError:
    def test_syntax_error(self):
        info = explain_error(Exception("syntax error at line 1"))
        assert info["error_type"] == "Синтаксическая ошибка SQL"
        assert "syntax error" in info["detail"]
        assert "suggestion" in info

    def test_permission_denied(self):
        info = explain_error(Exception("permission denied for table users"))
        assert info["error_type"] == "Нет прав доступа"

    def test_table_not_found(self):
        info = explain_error(Exception("relation 'orders' does not exist"))
        assert info["error_type"] == "Таблица не найдена"
        assert "orders" in info["detail"]

    def test_column_not_found(self):
        info = explain_error(Exception("column 'email' does not exist"))
        assert info["error_type"] == "Колонка не найдена"

    def test_timeout(self):
        info = explain_error(Exception("query timed out after 60s"))
        assert info["error_type"] == "Таймаут запроса"

    def test_db_unavailable(self):
        info = explain_error(Exception("connection refused"))
        assert info["error_type"] == "БД недоступна"

    def test_duplicate_key(self):
        info = explain_error(Exception("duplicate key value violates unique constraint"))
        assert info["error_type"] == "Конфликт данных"

    def test_type_error(self):
        info = explain_error(Exception("invalid input syntax for type integer"))
        assert info["error_type"] == "Ошибка типа данных"

    def test_deadlock(self):
        info = explain_error(Exception("transaction aborted: deadlock detected"))
        assert info["error_type"] == "Транзакция прервана"

    def test_oom(self):
        info = explain_error(Exception("out of memory"))
        assert info["error_type"] == "Недостаточно ресурсов"

    def test_unknown_error(self):
        info = explain_error(Exception("something weird happened"))
        assert info["error_type"] == "Неизвестная ошибка"
        assert "weird" in info["detail"]

    def test_multiline_error_detail_truncated(self):
        long_msg = "error\n" + "\n".join(f"line {i}" for i in range(50))
        info = explain_error(Exception(long_msg))
        assert len(info["detail"]) <= 300

    def test_empty_message(self):
        info = explain_error(Exception(""))
        assert info["error_type"] == "Неизвестная ошибка"


class TestFormatErrorResponse:
    def test_returns_markdown(self):
        out = format_error_response(Exception("syntax error"), context="sql_query")
        assert "❌" in out
        assert "**" in out
        assert "💡" in out
        assert "Подсказка" in out

    def test_includes_detail(self):
        out = format_error_response(Exception("table 'x' not found"))
        assert "x" in out

    def test_includes_context_in_suggestion(self):
        out = format_error_response(Exception("timeout"), context="sql_query")
        assert "Подсказка" in out


class TestGetSuggestions:
    def test_syntax_error_suggestion(self):
        s = _get_suggestions("Синтаксическая ошибка SQL", "")
        assert "DuckDB" in s or "sqlglot" in s.lower()

    def test_table_not_found_suggestion(self):
        s = _get_suggestions("Таблица не найдена", "")
        assert "get_schema" in s or "schema" in s.lower()

    def test_unknown_type_default(self):
        s = _get_suggestions("Случайный тип", "")
        assert "Проверьте" in s