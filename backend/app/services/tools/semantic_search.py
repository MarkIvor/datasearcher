from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="semantic_search",
    description="Семантический поиск по текстовым данным таблицы через LLM embeddings. Находит строки, похожие по смыслу на запрос. Требует LLM с поддержкой /v1/embeddings.",
    parameters={
        "type": "object",
        "properties": {
            "table_name": {"type": "string", "description": "Имя таблицы"},
            "text_column": {"type": "string", "description": "Текстовая колонка для поиска"},
            "query": {"type": "string", "description": "Поисковый запрос"},
            "top_k": {"type": "integer", "description": "Сколько результатов вернуть (по умолчанию 10)"},
            "where": {"type": "string", "description": "WHERE-условие (необязательно)"},
        },
        "required": ["table_name", "text_column", "query"],
    },
)
async def semantic_search(
    session: Session,
    table_name: str,
    text_column: str,
    query: str,
    top_k: int = 10,
    where: str = "",
) -> str:
    from ..engine import get_engine_for_session
    from ..embeddings import semantic_search as _ss
    eng = get_engine_for_session(session)

    # Если таблица remote — выгрузить в DuckDB
    ref = eng.get_table_ref(table_name)
    if ref and ref.connector_name and not ref.in_duckdb:
        try:
            eng.ensure_table_in_duckdb(table_name, columns=text_column, where=where)
        except Exception as e:
            return f"Не удалось выгрузить remote-таблицу: {e}"

    return await _ss(session, table_name, text_column, query, top_k=top_k, where=where)