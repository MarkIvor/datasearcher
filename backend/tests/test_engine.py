from __future__ import annotations

import os

import pytest

from app.services.engine import AnalysisEngine, _safe_table_name, _is_table_blocked, get_engine_for_session


class TestSafeTableName:
    def test_alphanumeric_preserved(self):
        assert _safe_table_name("orders_2024") == "orders_2024"

    def test_special_chars_replaced(self):
        assert _safe_table_name("my-table.name") == "my_table_name"

    def test_digit_prefix_gets_t_(self):
        assert _safe_table_name("2024orders").startswith("t_")

    def test_empty_returns_table(self):
        assert _safe_table_name("") == "table"

    def test_cyrillic_preserved(self):
        assert _safe_table_name("продажи") == "продажи"


class TestIsTableBlocked:
    def test_blocked_pattern_match(self):
        assert _is_table_blocked("raw_users", None, ["raw_*"]) is True

    def test_not_blocked_when_no_pattern_match(self):
        assert _is_table_blocked("users", None, ["raw_*"]) is False

    def test_blocked_multiple_patterns(self):
        assert _is_table_blocked("stg_orders", None, ["raw_*", "stg_*"]) is True
        assert _is_table_blocked("tmp_x", None, ["raw_*", "tmp_*"]) is True

    def test_allowed_schemas_pass(self):
        assert _is_table_blocked("mart.users", ["mart"], []) is False

    def test_allowed_schemas_block_other(self):
        assert _is_table_blocked("raw.users", ["mart"], []) is True

    def test_case_insensitive(self):
        assert _is_table_blocked("RAW_users", None, ["raw_*"]) is True


class TestEngineFileLoading:
    def test_load_csv_creates_table(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        fi = eng.load_csv(sample_csv, table_name="sample")
        assert fi is not None
        assert fi.table_name == "sample"
        assert fi.row_count == 7
        assert len(fi.columns) == 6
        # таблица доступна в DuckDB
        count = duckdb_session.conn.execute("SELECT COUNT(*) FROM sample").fetchone()[0]
        assert count == 7

    def test_load_csv_registers_in_engine_tables(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        eng.load_csv(sample_csv, table_name="sample")
        ref = eng.get_table_ref("sample")
        assert ref is not None
        assert ref.in_duckdb is True
        assert ref.file_type == "csv"

    def test_load_csv_file_not_found(self, duckdb_session):
        eng = get_engine_for_session(duckdb_session)
        fi = eng.load_csv("/nonexistent/path.csv")
        assert fi is None
        assert any("не найден" in e for e in eng.errors())

    def test_get_table_ref_missing(self, duckdb_session):
        eng = get_engine_for_session(duckdb_session)
        assert eng.get_table_ref("nonexistent") is None

    def test_register_file_table(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        fi = eng.load_csv(sample_csv, table_name="sample")
        # повторная регистрация не падает
        eng.register_file_table(fi)
        assert "sample" in eng.tables

    def test_available_tables(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        eng.load_csv(sample_csv, table_name="sample")
        assert "sample" in eng.available_tables()

    def test_tables_summary(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        eng.load_csv(sample_csv, table_name="sample")
        summary = eng.tables_summary()
        assert len(summary) == 1
        assert summary[0]["table_name"] == "sample"
        assert summary[0]["in_duckdb"] is True


class TestEngineSQLTranslation:
    def test_translate_no_connectors_returns_original(self, duckdb_session):
        eng = get_engine_for_session(duckdb_session)
        sql = "SELECT DATE_TRUNC('month', d) FROM t"
        assert eng.translate_sql(sql) == sql

    def test_translate_disabled(self, duckdb_session, monkeypatch):
        from app.services import engine as eng_mod
        monkeypatch.setattr(eng_mod.settings, "auto_translate", False)
        eng = get_engine_for_session(duckdb_session)
        assert eng.translate_sql("SELECT 1") == "SELECT 1"


class TestEngineRemote:
    def test_execute_remote_no_connectors_raises(self, duckdb_session):
        eng = get_engine_for_session(duckdb_session)
        with pytest.raises(RuntimeError, match="Нет подключённых"):
            eng.execute_remote("SELECT 1")

    def test_has_remote_tables_false_when_only_files(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        eng.load_csv(sample_csv, table_name="sample")
        assert eng.has_remote_tables() is False

    def test_ensure_table_in_duckdb_for_local_table(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        eng.load_csv(sample_csv, table_name="sample")
        # уже в duckdb — вернёт существующее имя
        name = eng.ensure_table_in_duckdb("sample")
        assert name == "sample"

    def test_ensure_table_in_duckdb_missing_raises(self, duckdb_session):
        eng = get_engine_for_session(duckdb_session)
        with pytest.raises(ValueError, match="не найдена"):
            eng.ensure_table_in_duckdb("nonexistent")


class TestEngineFKGraph:
    def test_fk_graph_empty(self, duckdb_session):
        eng = get_engine_for_session(duckdb_session)
        assert eng.fk_graph() == {}

    def test_find_join_keys_by_name_heuristic(self, duckdb_session, sample_csv):
        eng = get_engine_for_session(duckdb_session)
        eng.load_csv(sample_csv, table_name="sample")
        # создадим вторую таблицу с колонкой id
        duckdb_session.conn.execute('CREATE TABLE orders (id INT, sample_id INT, amount DOUBLE)')
        from app.session import FileInfo
        fi = FileInfo(id="file_orders", name="orders", table_name="orders", file_type="csv",
                      csv_path="", row_count=0, columns=[{"name": "id", "type": "INTEGER"},
                                                          {"name": "sample_id", "type": "INTEGER"},
                                                          {"name": "amount", "type": "DOUBLE"}])
        duckdb_session.files[fi.id] = fi
        eng.register_file_table(fi)
        keys = eng.find_join_keys("orders", "sample")
        # "id" общая колонка → должна найтись
        assert ("id", "id") in keys or len(keys) > 0


class TestEngineSingleton:
    def test_get_engine_creates_once(self, duckdb_session):
        e1 = get_engine_for_session(duckdb_session)
        e2 = get_engine_for_session(duckdb_session)
        assert e1 is e2

    def test_get_engine_syncs_new_files(self, duckdb_session):
        eng = get_engine_for_session(duckdb_session)
        # добавим FileInfo напрямую в session.files
        from app.session import FileInfo
        fi = FileInfo(id="x1", name="x", table_name="x_table", file_type="csv",
                      csv_path="", row_count=0, columns=[])
        duckdb_session.files[fi.id] = fi
        # при следующем get_engine — должна зарегистрироваться
        eng2 = get_engine_for_session(duckdb_session)
        assert "x_table" in eng2.tables