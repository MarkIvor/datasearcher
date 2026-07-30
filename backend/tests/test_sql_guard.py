from __future__ import annotations

from app.services.sql_guard import check_read_only


class TestReadOnlyGuard:
    def test_select_allowed(self):
        ok, _ = check_read_only("SELECT * FROM users")
        assert ok

    def test_with_cte_allowed(self):
        ok, _ = check_read_only("WITH t AS (SELECT 1) SELECT * FROM t")
        assert ok

    def test_explain_allowed(self):
        ok, _ = check_read_only("EXPLAIN SELECT * FROM users")
        assert ok

    def test_show_allowed(self):
        ok, _ = check_read_only("SHOW TABLES")
        assert ok

    def test_describe_allowed(self):
        ok, _ = check_read_only("DESCRIBE users")
        assert ok

    def test_values_allowed(self):
        ok, _ = check_read_only("VALUES (1, 2, 3)")
        assert ok

    def test_insert_blocked(self):
        ok, reason = check_read_only("INSERT INTO users VALUES (1)")
        assert not ok
        assert "INSERT" in reason

    def test_update_blocked(self):
        ok, reason = check_read_only("UPDATE users SET name='x' WHERE id=1")
        assert not ok
        assert "UPDATE" in reason

    def test_delete_blocked(self):
        ok, reason = check_read_only("DELETE FROM users WHERE id=1")
        assert not ok
        assert "DELETE" in reason

    def test_drop_blocked(self):
        ok, reason = check_read_only("DROP TABLE users")
        assert not ok
        assert "DROP" in reason

    def test_truncate_blocked(self):
        ok, _ = check_read_only("TRUNCATE users")
        assert not ok

    def test_alter_blocked(self):
        ok, _ = check_read_only("ALTER TABLE users ADD COLUMN x INT")
        assert not ok

    def test_create_blocked(self):
        ok, _ = check_read_only("CREATE TABLE foo (id INT)")
        assert not ok

    def test_insert_in_cte_blocked(self):
        ok, _ = check_read_only("WITH t AS (INSERT INTO x VALUES(1)) SELECT 1")
        assert not ok

    def test_empty_sql_allowed(self):
        ok, _ = check_read_only("")
        assert ok

    def test_whitespace_only_allowed(self):
        ok, _ = check_read_only("   \n\t  ")
        assert ok

    def test_case_insensitive(self):
        ok, _ = check_read_only("insert into users values (1)")
        assert not ok

    def test_multiple_statements_with_drop_blocked(self):
        # DROP во втором statement ловится проверкой тела — это правильно для read-only
        ok, _ = check_read_only("SELECT 1; DROP TABLE users")
        assert not ok

    def test_multiple_selects_allowed(self):
        ok, _ = check_read_only("SELECT 1; SELECT 2")
        assert ok


class TestReadOnlyGuardDisabled:
    def test_all_allowed_when_disabled(self, monkeypatch):
        from app.services import sql_guard
        monkeypatch.setattr(sql_guard.settings, "read_only", False)
        ok, reason = check_read_only("DROP TABLE users")
        assert ok
        assert reason == ""