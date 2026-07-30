from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from ..config import settings


class LoggingDB:
    """SQLite append-only лог запросов, ошибок и аудита.

    Таблицы:
    - query_log: каждый SQL-запрос (текст, время, длительность, результат)
    - error_log: ошибки обращения к БД (тип, сообщение, SQL)
    - audit_log: действия (attach, refresh, load_file, etc.)
    """

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or settings.log_db_path or os.path.join(
            os.getcwd(), "datasearcher_logs.db"
        )
        if not settings.log_enabled:
            return
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool TEXT NOT NULL,
                sql TEXT DEFAULT '',
                table_name TEXT DEFAULT '',
                connection TEXT DEFAULT '',
                rows_returned INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                success INTEGER DEFAULT 1,
                error TEXT DEFAULT '',
                user TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                error_type TEXT DEFAULT '',
                message TEXT DEFAULT '',
                sql TEXT DEFAULT '',
                connection TEXT DEFAULT '',
                stack TEXT DEFAULT '',
                tool TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT DEFAULT '',
                details TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_query_log_time ON query_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_error_log_time ON error_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_log_time ON audit_log(timestamp);
            """)

    def log_query(
        self,
        tool: str,
        sql: str = "",
        table_name: str = "",
        connection: str = "",
        rows_returned: int = 0,
        duration_ms: int = 0,
        success: bool = True,
        error: str = "",
        user: str = "",
    ) -> None:
        if not settings.log_enabled:
            return
        with self._conn() as c:
            c.execute(
                "INSERT INTO query_log (timestamp, tool, sql, table_name, connection, rows_returned, duration_ms, success, error, user) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (datetime.now().isoformat(), tool, sql, table_name, connection,
                 rows_returned, duration_ms, 1 if success else 0, error, user),
            )

    def log_error(
        self,
        error_type: str,
        message: str,
        sql: str = "",
        connection: str = "",
        stack: str = "",
        tool: str = "",
    ) -> None:
        if not settings.log_enabled:
            return
        with self._conn() as c:
            c.execute(
                "INSERT INTO error_log (timestamp, error_type, message, sql, connection, stack, tool) VALUES (?,?,?,?,?,?,?)",
                (datetime.now().isoformat(), error_type, message, sql, connection, stack, tool),
            )

    def log_audit(self, action: str, target: str = "", details: dict | None = None) -> None:
        if not settings.log_enabled:
            return
        with self._conn() as c:
            c.execute(
                "INSERT INTO audit_log (timestamp, action, target, details) VALUES (?,?,?,?)",
                (datetime.now().isoformat(), action, target,
                 json.dumps(details or {}, ensure_ascii=False, default=str)),
            )

    def get_query_logs(self, limit: int = 50) -> list[dict]:
        if not settings.log_enabled:
            return []
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM query_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_error_logs(self, limit: int = 50) -> list[dict]:
        if not settings.log_enabled:
            return []
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM error_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_audit_logs(self, limit: int = 50) -> list[dict]:
        if not settings.log_enabled:
            return []
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]


_log_db: LoggingDB | None = None


def get_log_db() -> LoggingDB:
    global _log_db
    if _log_db is None:
        _log_db = LoggingDB()
    return _log_db