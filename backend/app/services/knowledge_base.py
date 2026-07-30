from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from ..config import settings


class KnowledgeBase:
    """SQLite-хранилище метаописаний данных.

    Хранит:
    - table_meta: бизнес-описания таблиц, владельцы, слой (raw/staging/mart), теги
    - column_meta: описания колонок, единицы, PII-тип, чувствительность
    - metrics: расчётные метрики (имя, формула, описание, владелец)

    Источники наполнения (fallback-цепочка):
    1. Авто из схемы БД (DESCRIBE, information_schema)
    2. dbt manifest
    3. DataHub
    4. Ручная правка через update_metadata
    """

    def __init__(self, db_path: str = ""):
        self.db_path = db_path or settings.kb_db_path or os.path.join(
            os.getcwd(), "datasearcher_kb.db"
        )
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS table_meta (
                table_name TEXT NOT NULL,
                connection TEXT NOT NULL DEFAULT '',
                description TEXT DEFAULT '',
                owner TEXT DEFAULT '',
                layer TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                is_certified INTEGER DEFAULT 0,
                source TEXT DEFAULT '',
                PRIMARY KEY (table_name, connection)
            );

            CREATE TABLE IF NOT EXISTS column_meta (
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                description TEXT DEFAULT '',
                unit TEXT DEFAULT '',
                pii_type TEXT DEFAULT '',
                is_sensitive INTEGER DEFAULT 0,
                source TEXT DEFAULT '',
                PRIMARY KEY (table_name, column_name)
            );

            CREATE TABLE IF NOT EXISTS metrics (
                name TEXT PRIMARY KEY,
                formula TEXT DEFAULT '',
                description TEXT DEFAULT '',
                owner TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_column_meta_table ON column_meta(table_name);
            """)

    # ── table_meta ──────────────────────────────
    def upsert_table(
        self,
        table_name: str,
        connection: str = "",
        description: str | None = None,
        owner: str | None = None,
        layer: str | None = None,
        tags: list[str] | None = None,
        is_certified: bool | None = None,
        source: str = "",
    ) -> None:
        with self._conn() as c:
            existing = c.execute(
                "SELECT * FROM table_meta WHERE table_name=? AND connection=?",
                (table_name, connection),
            ).fetchone()
            if existing:
                updates = {}
                if description is not None:
                    updates["description"] = description
                if owner is not None:
                    updates["owner"] = owner
                if layer is not None:
                    updates["layer"] = layer
                if tags is not None:
                    updates["tags"] = json.dumps(tags, ensure_ascii=False)
                if is_certified is not None:
                    updates["is_certified"] = 1 if is_certified else 0
                if source:
                    updates["source"] = source
                if updates:
                    set_clause = ", ".join(f"{k}=?" for k in updates)
                    c.execute(
                        f"UPDATE table_meta SET {set_clause} WHERE table_name=? AND connection=?",
                        (*updates.values(), table_name, connection),
                    )
            else:
                c.execute(
                    "INSERT INTO table_meta (table_name, connection, description, owner, layer, tags, is_certified, source) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        table_name, connection,
                        description or "", owner or "", layer or "",
                        json.dumps(tags or [], ensure_ascii=False),
                        1 if is_certified else 0,
                        source,
                    ),
                )

    def get_table(self, table_name: str, connection: str = "") -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM table_meta WHERE table_name=? AND (connection=? OR connection='')",
                (table_name, connection),
            ).fetchone()
            if row:
                d = dict(row)
                d["tags"] = json.loads(d.get("tags", "[]"))
                return d
            return None

    def all_tables(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM table_meta ORDER BY table_name").fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["tags"] = json.loads(d.get("tags", "[]"))
                result.append(d)
            return result

    # ── column_meta ─────────────────────────────
    def upsert_column(
        self,
        table_name: str,
        column_name: str,
        description: str | None = None,
        unit: str | None = None,
        pii_type: str | None = None,
        is_sensitive: bool | None = None,
        source: str = "",
    ) -> None:
        with self._conn() as c:
            existing = c.execute(
                "SELECT * FROM column_meta WHERE table_name=? AND column_name=?",
                (table_name, column_name),
            ).fetchone()
            if existing:
                updates = {}
                if description is not None:
                    updates["description"] = description
                if unit is not None:
                    updates["unit"] = unit
                if pii_type is not None:
                    updates["pii_type"] = pii_type
                if is_sensitive is not None:
                    updates["is_sensitive"] = 1 if is_sensitive else 0
                if source:
                    updates["source"] = source
                if updates:
                    set_clause = ", ".join(f"{k}=?" for k in updates)
                    c.execute(
                        f"UPDATE column_meta SET {set_clause} WHERE table_name=? AND column_name=?",
                        (*updates.values(), table_name, column_name),
                    )
            else:
                c.execute(
                    "INSERT INTO column_meta (table_name, column_name, description, unit, pii_type, is_sensitive, source) VALUES (?,?,?,?,?,?,?)",
                    (
                        table_name, column_name,
                        description or "", unit or "", pii_type or "",
                        1 if is_sensitive else 0, source,
                    ),
                )

    def get_columns(self, table_name: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM column_meta WHERE table_name=? ORDER BY column_name",
                (table_name,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_column(self, table_name: str, column_name: str) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM column_meta WHERE table_name=? AND column_name=?",
                (table_name, column_name),
            ).fetchone()
            return dict(row) if row else None

    def get_pii_columns(self, table_name: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM column_meta WHERE table_name=? AND pii_type!='' AND pii_type IS NOT NULL",
                (table_name,),
            ).fetchall()
            return [dict(row) for row in rows]

    # ── metrics ─────────────────────────────────
    def upsert_metric(
        self,
        name: str,
        formula: str = "",
        description: str = "",
        owner: str = "",
    ) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO metrics (name, formula, description, owner) VALUES (?,?,?,?)",
                (name, formula, description, owner),
            )

    def get_metric(self, name: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM metrics WHERE name=?", (name,)).fetchone()
            return dict(row) if row else None

    def all_metrics(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM metrics ORDER BY name").fetchall()
            return [dict(row) for row in rows]

    def delete_metric(self, name: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM metrics WHERE name=?", (name,))
            return cur.rowcount > 0

    # ── search ──────────────────────────────────
    def search(self, query: str, limit: int = 10) -> list[dict]:
        q = f"%{query}%"
        results = []
        with self._conn() as c:
            rows = c.execute(
                """SELECT table_name, description, owner, layer, 'table' as type
                   FROM table_meta
                   WHERE table_name LIKE ? OR description LIKE ? OR owner LIKE ?
                   LIMIT ?""",
                (q, q, q, limit),
            ).fetchall()
            for row in rows:
                results.append(dict(row))
            rows = c.execute(
                """SELECT table_name, column_name, description, 'column' as type
                   FROM column_meta
                   WHERE column_name LIKE ? OR description LIKE ?
                   LIMIT ?""",
                (q, q, limit),
            ).fetchall()
            for row in rows:
                results.append(dict(row))
            rows = c.execute(
                """SELECT name, formula, description, 'metric' as type
                   FROM metrics
                   WHERE name LIKE ? OR description LIKE ? OR formula LIKE ?
                   LIMIT ?""",
                (q, q, q, limit),
            ).fetchall()
            for row in rows:
                results.append(dict(row))
        return results[:limit]


_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb