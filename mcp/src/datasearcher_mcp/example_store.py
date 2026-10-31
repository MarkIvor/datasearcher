from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
from typing import Any

import httpx
import numpy as np

from .config import settings
from .knowledge_base import get_kb


class ExampleStore:
    """Хранилище пар «NL-запрос → SQL → ответ» для few-shot (ТЗ 1.3, v2).

    Семантический поиск по прошлым запросам → улучшает generate_sql.
    Авто-наполнение после успешных вызовов generate_sql.
    """

    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(get_kb().db_path), "datasearcher_mcp_examples.db")
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                sql TEXT NOT NULL,
                table_name TEXT DEFAULT '',
                success INTEGER DEFAULT 1,
                embedding BLOB,
                created_at TEXT DEFAULT (datetime('now')),
                is_golden INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_examples_table ON examples(table_name);
            """)

    def add_example(
        self,
        query: str,
        sql: str,
        table_name: str = "",
        success: bool = True,
        is_golden: bool = False,
    ) -> int:
        """Сохранить пару запрос→SQL."""
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO examples (query, sql, table_name, success, is_golden) VALUES (?,?,?,?,?)",
                (query, sql, table_name, 1 if success else 0, 1 if is_golden else 0),
            )
            return cur.lastrowid

    def add_example_with_embedding(
        self,
        query: str,
        sql: str,
        table_name: str = "",
        success: bool = True,
        is_golden: bool = False,
    ) -> int:
        """Сохранить с embedding (async — вызывается из server)."""
        ex_id = self.add_example(query, sql, table_name, success, is_golden)
        return ex_id

    def all_examples(self, limit: int = 100) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM examples ORDER BY is_golden DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_by_table(self, table_name: str, limit: int = 10) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM examples WHERE table_name=? AND success=1 ORDER BY is_golden DESC, id DESC LIMIT ?",
                (table_name, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def search_similar(self, query: str, top_k: int = 3) -> list[dict]:
        """Семантический поиск похожих примеров (async — нужен LLM)."""
        # Эта функция вызывается через async wrapper
        raise NotImplementedError("Use async_search_similar")

    async def async_search_similar(self, query: str, top_k: int = 3) -> list[dict]:
        """Семантический поиск похожих примеров через LLM embeddings."""
        all_examples = self.all_examples(limit=500)
        if not all_examples:
            return []

        # Если нет embeddings — вычисляем для всех
        need_embeddings = [e for e in all_examples if not e.get("embedding")]
        if need_embeddings:
            try:
                query_embeddings = await self._get_embeddings_batch([e["query"] for e in need_embeddings])
                for ex, emb in zip(need_embeddings, query_embeddings):
                    self._update_embedding(ex["id"], emb)
                    ex["embedding"] = np.array(emb, dtype=np.float32).tobytes()
            except Exception:
                # Fallback: текстовый поиск
                return self._text_search(query, top_k)

        # Embedding для нового запроса
        try:
            query_emb = await self._get_embedding(query)
        except Exception:
            return self._text_search(query, top_k)

        query_vec = np.array(query_emb, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        scored = []
        for ex in all_examples:
            if not ex.get("embedding"):
                continue
            try:
                ex_vec = np.frombuffer(ex["embedding"], dtype=np.float32)
                ex_norm = np.linalg.norm(ex_vec)
                if ex_norm > 0 and query_norm > 0:
                    sim = float(np.dot(query_vec, ex_vec) / (query_norm * ex_norm))
                    scored.append((sim, ex))
            except Exception:
                continue

        scored.sort(key=lambda x: -x[0])
        return [ex for sim, ex in scored[:top_k]]

    def _text_search(self, query: str, top_k: int = 3) -> list[dict]:
        """Fallback: простой текстовый поиск по словам."""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored = []
        for ex in self.all_examples(limit=200):
            ex_words = set(ex["query"].lower().split())
            overlap = len(query_words & ex_words)
            if overlap > 0:
                scored.append((overlap, ex))
        scored.sort(key=lambda x: -x[0])
        return [ex for _, ex in scored[:top_k]]

    def _update_embedding(self, ex_id: int, embedding: list[float]) -> None:
        emb_bytes = np.array(embedding, dtype=np.float32).tobytes()
        with self._conn() as c:
            c.execute("UPDATE examples SET embedding=? WHERE id=?", (emb_bytes, ex_id))

    async def _get_embedding(self, text: str) -> list[float]:
        from .embeddings import _get_embedding
        return await _get_embedding(text)

    async def _get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        from .embeddings import _get_embeddings_batch
        return await _get_embeddings_batch(texts)


_example_store: ExampleStore | None = None


def get_example_store() -> ExampleStore:
    global _example_store
    if _example_store is None:
        _example_store = ExampleStore()
    return _example_store
