from __future__ import annotations

from typing import Any

from .base import Connector
from .clickhouse import ClickHouseConnector
from .mysql import MySQLConnector
from .postgres import PostgresConnector
from .sqlite_conn import SQLiteConnector
from .api import ApiConnector

_REGISTRY: dict[str, type[Connector]] = {
    "postgresql": PostgresConnector,
    "postgres": PostgresConnector,
    "mysql": MySQLConnector,
    "mariadb": MySQLConnector,
    "clickhouse": ClickHouseConnector,
    "sqlite": SQLiteConnector,
    "api": ApiConnector,
}


def supported_db_types() -> list[str]:
    return sorted(set(_REGISTRY.keys()))


def get_connector(name: str, db_type: str, params: dict) -> Connector:
    db_type = (db_type or "").lower().strip()
    cls = _REGISTRY.get(db_type)
    if cls is None:
        raise ValueError(
            f"Неподдерживаемый тип БД: {db_type!r}. "
            f"Поддерживаются: {supported_db_types()}"
        )
    return cls(name=name, params=params)