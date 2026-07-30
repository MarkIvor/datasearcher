from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import httpx
import numpy as np

from ..config import settings
from ..session import Session


def _cache_path(eng_dir: str, table: str, column: str) -> str:
    key = hashlib.md5(f"{table}.{column}".encode()).hexdigest()[:12]
    return os.path.join(eng_dir, f"emb_{table}_{column}_{key}.json")


def _query_hash(rows: list[tuple]) -> str:
    return hashlib.md5(json.dumps(rows, default=str).encode()).hexdigest()[:12]


async def _get_embedding(text: str) -> list[float]:
    """Получить embedding через OpenAI-compatible /v1/embeddings."""
    if not settings.llm_base_url or not settings.llm_model:
        raise RuntimeError(
            "Для semantic_search нужен LLM API. Настройте LLM_BASE_URL и LLM_MODEL."
        )
    url = f"{settings.llm_base_url.rstrip('/')}/embeddings"
    payload = {"model": settings.llm_model, "input": text}
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


async def _get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch embeddings через /v1/embeddings."""
    if not settings.llm_base_url or not settings.llm_model:
        raise RuntimeError(
            "Для semantic_search нужен LLM API. Настройте LLM_BASE_URL и LLM_MODEL."
        )
    url = f"{settings.llm_base_url.rstrip('/')}/embeddings"
    all_embeddings: list[list[float]] = []
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(texts), 100):
            batch = texts[i:i + 100]
            payload = {"model": settings.llm_model, "input": batch}
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            for item in sorted(data["data"], key=lambda x: x["index"]):
                all_embeddings.append(item["embedding"])

    return all_embeddings


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    norms_a = np.linalg.norm(a, axis=1, keepdims=True)
    norms_b = np.linalg.norm(b)
    norms_a[norms_a == 0] = 1
    denom = norms_a.flatten() * (norms_b if norms_b else 1)
    return (a @ b) / denom


def _get_embeddings_dir() -> str:
    eng_dir = settings.embeddings_dir or os.path.join(
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "datasearcher_embeddings",
    )
    os.makedirs(eng_dir, exist_ok=True)
    return eng_dir


async def semantic_search(
    session: Session,
    table_name: str,
    text_column: str,
    query: str,
    top_k: int = 10,
    where: str = "",
) -> str:
    """Семантический поиск через LLM embeddings."""
    conn = session.conn

    where_clause = f" WHERE {where}" if where.strip() else ""
    try:
        if where_clause:
            result = conn.execute(
                f'SELECT rowid, "{text_column}" FROM "{table_name}"{where_clause} '
                f'AND "{text_column}" IS NOT NULL LIMIT {settings.semantic_search_max_rows}'
            )
        else:
            result = conn.execute(
                f'SELECT rowid, "{text_column}" FROM "{table_name}" '
                f'WHERE "{text_column}" IS NOT NULL LIMIT {settings.semantic_search_max_rows}'
            )
        rows = result.fetchall()
    except Exception as e:
        return f"Ошибка: {e}"

    if not rows:
        return "Нет данных для поиска."

    if len(rows) > settings.semantic_search_max_rows:
        return f"Слишком много строк ({len(rows)}). Лимит: {settings.semantic_search_max_rows}."

    texts = [str(r[1]) for r in rows]

    cache_file = _cache_path(_get_embeddings_dir(), table_name, text_column)
    content_hash = _query_hash(rows)
    cached: dict = {}
    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
        except Exception:
            cached = {}

    need_indices = [i for i, t in enumerate(texts) if str(hash(t)) not in cached.get("texts", {})]
    if cached.get("hash") != content_hash:
        cached = {"hash": content_hash, "texts": {}, "embeddings": []}
        need_indices = list(range(len(texts)))

    if need_indices:
        try:
            new_texts = [texts[i] for i in need_indices]
            new_embs = await _get_embeddings_batch(new_texts)
            if not cached.get("embeddings"):
                cached["embeddings"] = [None] * len(texts)
            for idx, emb in zip(need_indices, new_embs):
                while len(cached["embeddings"]) <= idx:
                    cached["embeddings"].append(None)
                cached["embeddings"][idx] = emb
            cached["hash"] = content_hash
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached, f)
        except Exception as e:
            return f"Ошибка получения embeddings: {e}\nНастройте LLM_BASE_URL/LLM_MODEL с поддержкой /v1/embeddings."

    try:
        query_emb = await _get_embedding(query)
    except Exception as e:
        return f"Ошибка получения embedding запроса: {e}"

    embs = np.array(cached["embeddings"])
    q = np.array(query_emb)
    similarities = embs @ q / (
        np.linalg.norm(embs, axis=1) * np.linalg.norm(q) + 1e-10
    )

    top_indices = np.argsort(similarities)[::-1][:top_k]

    from .tools.registry import format_table
    out_rows = []
    for idx in top_indices:
        row = rows[idx]
        out_rows.append((row[0], str(row[1])[:200], round(float(similarities[idx]), 4)))

    out = [
        f"# Семантический поиск: '{query}'",
        f"Таблица: {table_name}.{text_column}, проверено {len(rows)} строк",
        f"Топ-{len(out_rows)} похожих:",
        "",
        format_table(["rowid", text_column, "similarity"], out_rows),
    ]
    return "\n".join(out)