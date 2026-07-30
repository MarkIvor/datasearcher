from __future__ import annotations

import os
import sqlite3

import pytest

from app.services.connectors import get_connector, supported_db_types
from app.services.connectors.base import Connector
from app.services.connectors.sqlite_conn import SQLiteConnector
from app.services.connectors.api import ApiConnector, _extract_items, _flatten_records, _flatten_keys, _flatten_dict
from app.services.connectors.registry import _REGISTRY


class TestRegistry:
    def test_supported_db_types_includes_all(self):
        types = supported_db_types()
        assert "postgresql" in types
        assert "mysql" in types
        assert "clickhouse" in types
        assert "sqlite" in types
        assert "api" in types

    def test_postgres_alias(self):
        assert _REGISTRY["postgres"] is _REGISTRY["postgresql"]

    def test_mariadb_alias(self):
        assert _REGISTRY["mariadb"] is _REGISTRY["mysql"]

    def test_get_connector_sqlite(self):
        c = get_connector("test", "sqlite", {"database": ":memory:"})
        assert isinstance(c, SQLiteConnector)
        assert c.name == "test"

    def test_get_connector_api(self):
        c = get_connector("test", "api", {"base_url": "https://x.com", "endpoints": []})
        assert isinstance(c, ApiConnector)

    def test_get_connector_unsupported_raises(self):
        with pytest.raises(ValueError, match="Неподдерживаемый"):
            get_connector("x", "oracle", {})

    def test_get_connector_case_insensitive(self):
        c = get_connector("t", "PostgreSQL", {"host": "x", "port": 5432, "database": "d", "username": "u", "password": "p"})
        assert c.db_type == "postgresql"


class TestSQLiteConnector:
    @pytest.fixture()
    def sqlite_db(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT);
            INSERT INTO users VALUES (1, 'Анна', 'anna@example.com');
            INSERT INTO users VALUES (2, 'Борис', 'boris@mail.com');
            INSERT INTO users VALUES (3, 'Вика', 'vika@company.org');
            CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL);
            INSERT INTO orders VALUES (1, 1, 1500.0);
            INSERT INTO orders VALUES (2, 2, 2300.0);
        """)
        conn.commit()
        conn.close()
        return str(db_path)

    def test_test_success(self, sqlite_db):
        c = SQLiteConnector("test", {"database": sqlite_db})
        assert c.test() is True

    def test_test_failure_missing_file(self, tmp_path):
        c = SQLiteConnector("x", {"database": str(tmp_path / "nonexistent.db")})
        assert c.test() is False

    def test_list_tables(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        tables = c.list_tables()
        assert "users" in tables
        assert "orders" in tables

    def test_fetch_table(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        cols, rows = c.fetch_table("users", limit=10)
        assert "id" in cols
        assert "name" in cols
        assert len(rows) == 3

    def test_fetch_table_limit(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        cols, rows = c.fetch_table("users", limit=2)
        assert len(rows) == 2

    def test_execute_sql(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        cols, rows = c.execute_sql("SELECT COUNT(*) AS n FROM users")
        assert rows[0][0] == 3

    def test_row_count(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        assert c.row_count("users") == 3
        assert c.row_count("orders") == 2

    def test_describe(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        cols = c.describe("users")
        assert any(col["name"] == "id" for col in cols)
        assert any(col["name"] == "email" for col in cols)

    def test_dialect(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        assert c.dialect() == "sqlite"

    def test_foreign_keys(self, sqlite_db):
        # Создаём БД с FK
        conn = sqlite3.connect(str(sqlite_db))
        conn.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );
        """)
        conn.commit()
        conn.close()
        c = SQLiteConnector("t", {"database": sqlite_db})
        fks = c.foreign_keys("items")
        assert len(fks) == 1
        assert fks[0]["column"] == "order_id"
        assert fks[0]["ref_table"] == "orders"

    def test_attach_duckdb_syntax(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        sql = c.attach_duckdb_syntax("my_alias")
        assert "ATTACH" in sql
        assert "my_alias" in sql
        assert "sqlite" in sql.lower()

    def test_quote(self, sqlite_db):
        c = SQLiteConnector("t", {"database": sqlite_db})
        assert c.quote("users") == '"users"'


class TestApiConnector:
    def test_list_tables_from_endpoints(self):
        c = ApiConnector("api", {
            "base_url": "https://api.example.com/v1",
            "endpoints": [
                {"path": "/customers", "table_name": "customers"},
                {"path": "/orders", "table_name": "orders"},
            ],
        })
        assert c.list_tables() == ["customers", "orders"]

    def test_list_tables_fallback_to_path(self):
        c = ApiConnector("api", {
            "base_url": "https://api.example.com",
            "endpoints": [{"path": "/products"}],
        })
        assert c.list_tables() == ["products"]

    def test_test_no_endpoints(self):
        c = ApiConnector("api", {"base_url": "https://x.com", "endpoints": []})
        assert c.test() is False

    def test_execute_sql_not_supported(self):
        c = ApiConnector("api", {"base_url": "https://x.com", "endpoints": []})
        with pytest.raises(NotImplementedError, match="dump"):
            c.execute_sql("SELECT 1")

    def test_find_endpoint_by_table_name(self):
        c = ApiConnector("api", {
            "base_url": "https://x.com",
            "endpoints": [{"path": "/items", "table_name": "items"}],
        })
        ep = c._find_endpoint("items")
        assert ep is not None
        assert ep["path"] == "/items"

    def test_find_endpoint_by_path_fallback(self):
        c = ApiConnector("api", {
            "base_url": "https://x.com",
            "endpoints": [{"path": "/things", "table_name": ""}],
        })
        ep = c._find_endpoint("things")
        assert ep is not None

    def test_find_endpoint_missing(self):
        c = ApiConnector("api", {"base_url": "https://x.com", "endpoints": []})
        assert c._find_endpoint("nonexistent") is None


class TestApiHelpers:
    def test_extract_items_from_list(self):
        assert _extract_items([{"a": 1}, {"b": 2}]) == [{"a": 1}, {"b": 2}]

    def test_extract_items_from_data_key(self):
        assert _extract_items({"data": [1, 2, 3]}) == [1, 2, 3]

    def test_extract_items_from_results_key(self):
        assert _extract_items({"results": [1, 2]}) == [1, 2]

    def test_extract_items_from_items_key(self):
        assert _extract_items({"items": ["a", "b"]}) == ["a", "b"]

    def test_extract_items_from_records_key(self):
        assert _extract_items({"records": [1]}) == [1]

    def test_extract_items_from_rows_key(self):
        assert _extract_items({"rows": [1, 2, 3]}) == [1, 2, 3]

    def test_extract_items_single_dict(self):
        result = _extract_items({"x": 1})
        assert result == [{"x": 1}]

    def test_extract_items_empty(self):
        assert _extract_items(None) == []
        assert _extract_items(123) == []

    def test_flatten_keys_flat(self):
        assert _flatten_keys({"a": 1, "b": 2}) == {"a", "b"}

    def test_flatten_keys_nested(self):
        keys = _flatten_keys({"user": {"name": "x", "email": "y"}})
        assert "user.name" in keys
        assert "user.email" in keys

    def test_flatten_dict(self):
        result = _flatten_dict({"user": {"name": "Anna"}, "age": 30})
        assert result["user.name"] == "Anna"
        assert result["age"] == 30

    def test_flatten_dict_with_list(self):
        result = _flatten_dict({"tags": ["a", "b"]})
        assert "tags" in result
        assert isinstance(result["tags"], str)

    def test_flatten_records(self):
        records = [
            {"name": "Anna", "email": "a@b.com"},
            {"name": "Boris"},
        ]
        cols, rows = _flatten_records(records)
        assert "name" in cols
        assert "email" in cols
        assert len(rows) == 2
        assert rows[1][cols.index("email")] is None


class TestConnectorBase:
    def test_base_quote(self):
        class Dummy(Connector):
            def test(self): return True
            def list_tables(self): return []
            def fetch_table(self, table, limit=50000): return [], []
            def row_count(self, table): return 0
        d = Dummy()
        assert d.quote("tbl") == '"tbl"'

    def test_base_describe_fallback(self):
        class Dummy(Connector):
            def test(self): return True
            def list_tables(self): return []
            def fetch_table(self, table, limit=50000): return ["a", "b"], [(1,)]
            def row_count(self, table): return 0
        d = Dummy()
        desc = d.describe("x")
        assert len(desc) == 2
        assert desc[0]["name"] == "a"

    def test_base_execute_sql_not_implemented(self):
        class Dummy(Connector):
            def test(self): return True
            def list_tables(self): return []
            def fetch_table(self, table, limit=50000): return [], []
            def row_count(self, table): return 0
        d = Dummy()
        with pytest.raises(NotImplementedError):
            d.execute_sql("SELECT 1")