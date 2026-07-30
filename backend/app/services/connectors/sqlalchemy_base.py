from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from .base import Connector


class SQLAlchemyConnector(Connector):
    """Общий коннектор для реляционных БД через SQLAlchemy.

    Подклассы определяют ``_build_url`` и (опционально) ``_list_tables_sql``.
    """

    db_type = "sqlalchemy"

    def __init__(self, name: str, params: dict):
        self.name = name
        self.params = params
        self._engine: Engine | None = None

    # ── методы для переопределения ──────────────
    def _build_url(self) -> str:
        raise NotImplementedError

    def _default_schema(self) -> str | None:
        return None

    def _list_tables_sql(self, schema: str | None) -> str | None:
        return None

    def _supports_inspect(self) -> bool:
        return True

    def dialect(self) -> str:
        return self.db_type

    def foreign_keys(self, table: str) -> list[dict]:
        return []

    def attach_duckdb_syntax(self, alias: str) -> str:
        raise NotImplementedError(f"{self.db_type} не поддерживает federated ATTACH")

    # ── движок ──────────────────────────────────
    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(self._build_url(), pool_pre_ping=True)
        return self._engine

    def test(self) -> bool:
        try:
            with self.engine.connect() as c:
                c.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def list_tables(self) -> list[str]:
        schema = self.params.get("schema") or self.params.get("schemas")
        if isinstance(schema, list):
            schemas: list[str | None] = schema
        else:
            schemas = [schema]

        if not schemas or all(s is None for s in schemas):
            schemas = [self._default_schema()]

        sql = self._list_tables_sql(None)
        if sql:
            try:
                with self.engine.connect() as c:
                    rows = c.execute(text(sql)).fetchall()
                return [r[0] for r in rows]
            except Exception:
                pass

        if not self._supports_inspect():
            return []

        insp = inspect(self.engine)
        tables: list[str] = []
        for sch in schemas:
            try:
                tables.extend(insp.get_table_names(schema=sch))
            except Exception:
                continue
        return tables

    def fetch_table(self, table: str, limit: int = 50000) -> tuple[list[str], list[tuple]]:
        q = self.quote(table)
        with self.engine.connect() as c:
            result = c.execute(text(f"SELECT * FROM {q} LIMIT {int(limit)}"))
            cols = list(result.keys())
            rows = result.fetchall()
        return cols, [tuple(r) for r in rows]

    def execute_sql(self, sql: str) -> tuple[list[str], list[tuple]]:
        """Push-down: выполнить SQL в source DB с timeout."""
        from ...config import settings
        timeout = settings.query_timeout
        with self.engine.connect() as c:
            if timeout > 0:
                c = c.execution_options(timeout=timeout)
            result = c.execute(text(sql))
            cols = list(result.keys())
            rows = result.fetchall()
        return cols, [tuple(r) for r in rows]

    def row_count(self, table: str) -> int:
        q = self.quote(table)
        try:
            with self.engine.connect() as c:
                row = c.execute(text(f"SELECT COUNT(*) FROM {q}")).fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    def describe(self, table: str) -> list[dict]:
        if not self._supports_inspect():
            return super().describe(table)
        try:
            insp = inspect(self.engine)
            schema = self.params.get("schema")
            cols_info = insp.get_columns(table, schema=schema) if schema else insp.get_columns(table)
            return [{"name": c["name"], "type": str(c.get("type", "unknown"))} for c in cols_info]
        except Exception:
            return super().describe(table)

    def foreign_keys(self, table: str) -> list[dict]:
        if not self._supports_inspect():
            return []
        try:
            insp = inspect(self.engine)
            schema = self.params.get("schema")
            fks = insp.get_foreign_keys(table, schema=schema) if schema else insp.get_foreign_keys(table)
            result = []
            for fk in fks:
                result.append({
                    "column": fk.get("constrained_columns", [None])[0],
                    "ref_table": fk.get("referred_table", ""),
                    "ref_column": (fk.get("referred_columns", [None]) or [None])[0],
                })
            return [r for r in result if r["column"] and r["ref_table"]]
        except Exception:
            return []