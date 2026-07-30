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
    uploaded_at: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    id: str
    conn: duckdb.DuckDBPyConnection
    files: dict[str, FileInfo] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def touch(self):
        self.last_activity = datetime.now()


class SessionManager:
    def __init__(self, memory_limit: str = "2GB"):
        self._sessions: dict[str, Session] = {}
        self._memory_limit = memory_limit

    def create(self) -> Session:
        session_id = uuid.uuid4().hex[:16]
        conn = duckdb.connect()
        conn.execute(f"SET memory_limit='{self._memory_limit}'")
        conn.execute("SET threads=4")
        session = Session(id=session_id, conn=conn)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id:
            session = self.get(session_id)
            if session:
                session.touch()
                return session
        return self.create()

    def delete(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            try:
                session.conn.close()
            except Exception:
                pass
            for fi in session.files.values():
                try:
                    Path(fi.csv_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def cleanup_expired(self, ttl_minutes: int = 60):
        cutoff = datetime.now().timestamp() - ttl_minutes * 60
        expired = [
            sid
            for sid, s in self._sessions.items()
            if s.last_activity.timestamp() < cutoff
        ]
        for sid in expired:
            self.delete(sid)
