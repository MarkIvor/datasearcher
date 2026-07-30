from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="refresh_schema",
    description="Обновить схему подключений — перечитать список таблиц, колонок и внешних ключей из source БД. Используй если структура БД изменилась.",
    parameters={
        "type": "object",
        "properties": {
            "connection": {"type": "string", "description": "Имя подключения (пусто = обновить все)"},
        },
    },
)
def refresh_schema(session: Session, connection: str = "") -> str:
    from ..engine import get_engine_for_session
    eng = get_engine_for_session(session)

    added, errors = eng.refresh_connector(connection)
    out = [
        f"✅ Схема обновлена. Таблиц: {len(eng.tables)} (добавлено/обновлено: {added}).",
    ]
    if errors:
        out.append("")
        out.append("Ошибки:")
        for e in errors[:10]:
            out.append(f"  - {e}")
    return "\n".join(out)