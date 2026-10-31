from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import duckdb


@dataclass
class FileInfo:
    id: str
    name: str
    table_name: str
    file_type: str
    csv_path: str
    row_count: int
    columns: list[dict]
    source: str = ""
    uploaded_at: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    """Совместимая с инструментами DataSearcher сессия.

    Инструменты ожидают: session.conn (DuckDB), session.files (dict[FileInfo]),
    session.id, session._exports.

    conn создаётся лениво через ensure_conn() — DuckDB не инициализируется
    пока не нужен (remote-режим).
    """

    id: str
    _conn: duckdb.DuckDBPyConnection | None = None
    files: dict[str, FileInfo] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    # runtime-атрибуты, используемые отдельными инструментами
    _exports: dict = field(default_factory=dict)

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect()
            self._conn.execute(f"SET memory_limit='{_DEFAULT_MEMORY}'")
            self._conn.execute(f"SET threads={_DEFAULT_THREADS}")
        return self._conn

    @conn.setter
    def conn(self, value):
        self._conn = value

    def touch(self):
        self.last_activity = datetime.now()

    def available_tables(self) -> set[str]:
        return {fi.table_name for fi in self.files.values()}

    def table_info_list(self) -> list[dict]:
        return [
            {
                "table_name": fi.table_name,
                "file_type": fi.file_type,
                "row_count": fi.row_count,
                "columns": fi.columns,
                "source": fi.source,
            }
            for fi in self.files.values()
        ]


_DEFAULT_MEMORY = "2GB"
_DEFAULT_THREADS = 4


class SessionManager:
    def __init__(self, memory_limit: str = "2GB", threads: int = 4):
        global _DEFAULT_MEMORY, _DEFAULT_THREADS
        _DEFAULT_MEMORY = memory_limit
        _DEFAULT_THREADS = threads

    def create(self) -> Session:
        session_id = uuid.uuid4().hex[:16]
        return Session(id=session_id)
