from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Connector(ABC):
    """Абстрактный коннектор к источнику данных.

    Поддерживает два режима:
    - **remote** (push-down): SQL выполняется в source DB через ``execute_sql``
    - **dump**: таблицы выгружаются в DuckDB через ``fetch_table``
    """

    db_type: str = "unknown"
    name: str = ""

    @abstractmethod
    def test(self) -> bool:
        """Проверка доступности источника."""

    @abstractmethod
    def list_tables(self) -> list[str]:
        """Список таблиц/листов/коллекций в источнике."""

    @abstractmethod
    def fetch_table(self, table: str, limit: int = 50000) -> tuple[list[str], list[tuple]]:
        """Выгрузка таблицы: (колонки, строки)."""

    @abstractmethod
    def row_count(self, table: str) -> int:
        """Полное число строк таблицы в источнике (без выгрузки)."""

    def execute_sql(self, sql: str) -> tuple[list[str], list[tuple]]:
        """Выполнение произвольного SQL в source DB (push-down)."""
        raise NotImplementedError(f"{self.db_type} не поддерживает execute_sql")

    def quote(self, table: str) -> str:
        return f'"{table}"'

    def dialect(self) -> str:
        """sqlglot-имя диалекта для трансляции SQL."""
        return "duckdb"

    def foreign_keys(self, table: str) -> list[dict]:
        """Внешние ключи таблицы: [{column, ref_table, ref_column}]."""
        return []

    def attach_duckdb_syntax(self, alias: str) -> str:
        """SQL для ATTACH к DuckDB через расширение (federated)."""
        raise NotImplementedError(f"{self.db_type} не поддерживает federated ATTACH")

    def describe(self, table: str) -> list[dict]:
        """Описания колонок: [{name, type}]."""
        try:
            cols, _ = self.fetch_table(table, limit=1)
            return [{"name": c, "type": "unknown"} for c in cols]
        except Exception:
            return []