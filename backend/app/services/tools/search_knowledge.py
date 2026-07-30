from __future__ import annotations

import json

from app.session import Session
from .registry import format_table, register_tool


@register_tool(
    name="search_knowledge",
    description="Поиск по Knowledge Base (бизнес-описания таблиц/колонок/метрик) и Example Store (эталонные NL→SQL пары). Используй для поиска метаданных и похожих примеров.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Поисковый запрос"},
            "top_k": {"type": "integer", "description": "Сколько результатов (по умолчанию 5)"},
        },
        "required": ["query"],
    },
)
async def search_knowledge(session: Session, query: str, top_k: int = 5) -> str:
    from ..knowledge_base import get_kb
    from ..example_store import get_example_store

    kb = get_kb()
    results = kb.search(query, limit=top_k)

    out = [f"# Поиск по Knowledge Base: '{query}'", ""]

    if results:
        out.append("## Метаданные")
        rows = []
        for r in results:
            if r.get("type") == "table":
                rows.append((r.get("table_name", ""), "table", (r.get("description") or "")[:60]))
            elif r.get("type") == "column":
                rows.append((f"{r.get('table_name', '')}.{r.get('column_name', '')}", "column", (r.get("description") or "")[:60]))
            elif r.get("type") == "metric":
                rows.append((r.get("name", ""), "metric", (r.get("description") or "")[:60]))
        out.append(format_table(["name", "type", "description"], rows))
    else:
        out.append("Метаданные не найдены.")

    store = get_example_store()
    if store is not None:
        try:
            similar = await store.async_search_similar(query, top_k=top_k)
        except Exception:
            similar = store._text_search(query, top_k)
        out.append("")
        out.append("## Похожие примеры (Example Store)")
        if similar:
            rows = [
                (e.get("query", "")[:80], e.get("sql", "")[:80], "⭐" if e.get("is_golden") else "")
                for e in similar
            ]
            out.append(format_table(["query", "sql", "golden"], rows))
        else:
            out.append("Похожие примеры не найдены.")

    return "\n".join(out)