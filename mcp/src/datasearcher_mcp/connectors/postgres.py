from __future__ import annotations

from .sqlalchemy_base import SQLAlchemyConnector


class PostgresConnector(SQLAlchemyConnector):
    db_type = "postgresql"

    def _build_url(self) -> str:
        p = self.params
        user = p.get("username") or p.get("user", "")
        pwd = p.get("password", "")
        host = p.get("host", "localhost")
        port = p.get("port") or 5432
        db = p.get("database", "")
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

    def _default_schema(self) -> str | None:
        return "public"

    def _list_tables_sql(self, schema: str | None) -> str | None:
        s = schema or "public"
        return f"SELECT tablename FROM pg_tables WHERE schemaname='{s}' ORDER BY tablename"

    def dialect(self) -> str:
        return "postgres"

    def attach_duckdb_syntax(self, alias: str) -> str:
        p = self.params
        user = p.get("username") or p.get("user", "")
        pwd = p.get("password", "")
        host = p.get("host", "localhost")
        port = p.get("port") or 5432
        db = p.get("database", "")
        return f"ATTACH 'host={host} port={port} dbname={db} user={user} password={pwd}' AS {alias} (TYPE postgres_scanner)"
