from __future__ import annotations

from .sqlalchemy_base import SQLAlchemyConnector


class MySQLConnector(SQLAlchemyConnector):
    """MySQL и MariaDB (через pymysql)."""

    db_type = "mysql"

    def _build_url(self) -> str:
        p = self.params
        user = p.get("username") or p.get("user", "")
        pwd = p.get("password", "")
        host = p.get("host", "localhost")
        port = p.get("port") or 3306
        db = p.get("database", "")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}?charset=utf8mb4"

    def _default_schema(self) -> str | None:
        return None

    def _list_tables_sql(self, schema: str | None) -> str | None:
        return "SHOW TABLES"

    def quote(self, table: str) -> str:
        return f"`{table}`"

    def dialect(self) -> str:
        return "mysql"

    def attach_duckdb_syntax(self, alias: str) -> str:
        p = self.params
        user = p.get("username") or p.get("user", "")
        pwd = p.get("password", "")
        host = p.get("host", "localhost")
        port = p.get("port") or 3306
        db = p.get("database", "")
        return f"ATTACH 'host={host} port={port} user={user} password={pwd} database={db}' AS {alias} (TYPE mysql_scanner)"
