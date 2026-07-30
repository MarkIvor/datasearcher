from __future__ import annotations

import time

import pytest

from app.services.rate_limiter import check_rate_limit, rate_limit_message, _category, _ML_TOOLS


class TestCategory:
    def test_sql_category(self):
        assert _category("sql_query") == "sql"
        assert _category("get_schema") == "sql"
        assert _category("export_data") == "sql"

    def test_ml_category(self):
        assert _category("cluster_analysis") == "ml"
        assert _category("predict_trend") == "ml"
        assert _category("semantic_search") == "ml"
        assert _category("auto_insights") == "ml"

    def test_all_ml_tools_categorized(self):
        for t in _ML_TOOLS:
            assert _category(t) == "ml"


class TestCheckRateLimit:
    def test_allowed_under_limit(self, monkeypatch):
        from app.services import rate_limiter
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_enabled", True)
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_sql", 60)
        # очищаем state
        rate_limiter._calls.clear()
        ok, wait = check_rate_limit("sql_query", "user1")
        assert ok is True
        assert wait == 0

    def test_blocks_over_limit(self, monkeypatch):
        from app.services import rate_limiter
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_enabled", True)
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_sql", 3)
        rate_limiter._calls.clear()
        # первые 3 — ок
        for _ in range(3):
            ok, _ = check_rate_limit("sql_query", "user_blocked")
            assert ok
        # 4-й — блок
        ok, wait = check_rate_limit("sql_query", "user_blocked")
        assert not ok
        assert wait >= 1

    def test_ml_limit_separate_from_sql(self, monkeypatch):
        from app.services import rate_limiter
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_enabled", True)
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_sql", 60)
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_ml", 2)
        rate_limiter._calls.clear()
        # 2 ML — ок, 3-й блок
        for _ in range(2):
            ok, _ = check_rate_limit("cluster_analysis", "u")
            assert ok
        ok, wait = check_rate_limit("cluster_analysis", "u")
        assert not ok
        assert wait >= 1

    def test_different_users_independent(self, monkeypatch):
        from app.services import rate_limiter
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_enabled", True)
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_sql", 2)
        rate_limiter._calls.clear()
        # user_a исчерпал лимит
        check_rate_limit("sql_query", "user_a")
        check_rate_limit("sql_query", "user_a")
        ok_a, _ = check_rate_limit("sql_query", "user_a")
        assert not ok_a
        # user_b — может
        ok_b, _ = check_rate_limit("sql_query", "user_b")
        assert ok_b

    def test_disabled_returns_true(self, monkeypatch):
        from app.services import rate_limiter
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_enabled", False)
        rate_limiter._calls.clear()
        for _ in range(100):
            ok, wait = check_rate_limit("sql_query", "u")
            assert ok
            assert wait == 0

    def test_window_sliding(self, monkeypatch):
        from app.services import rate_limiter
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_enabled", True)
        monkeypatch.setattr(rate_limiter.settings, "rate_limit_sql", 2)
        rate_limiter._calls.clear()
        check_rate_limit("sql_query", "slide_u")
        check_rate_limit("sql_query", "slide_u")
        # подменим timestamps на старые (>60 сек назад)
        key = ("sql", "slide_u")
        rate_limiter._calls[key] = [time.time() - 61, time.time() - 61]
        # теперь должен опять разрешить
        ok, _ = check_rate_limit("sql_query", "slide_u")
        assert ok


class TestRateLimitMessage:
    def test_sql_message(self):
        msg = rate_limit_message("sql_query", 30)
        assert "60" in msg
        assert "30" in msg
        assert "sql" in msg

    def test_ml_message(self):
        msg = rate_limit_message("cluster_analysis", 15)
        assert "10" in msg
        assert "ml" in msg