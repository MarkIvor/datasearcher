from __future__ import annotations

from app.session import Session
from .registry import register_tool


@register_tool(
    name="test_connection",
    description="Проверить доступность подключения к БД. Возвращает статус OK/FAIL.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Имя подключения"},
        },
        "required": ["name"],
    },
)
def test_connection(session: Session, name: str) -> str:
    from ..engine import get_engine_for_session
    eng = get_engine_for_session(session)

    connector = eng.get_connector_by_name(name)
    if connector is None:
        return f"❌ Подключение '{name}' не найдено. Доступные: {list(eng.connectors.keys())}"

    ok = connector.test()
    if ok:
        return f"✅ Подключение '{name}' ({connector.db_type}) доступно."
    return f"❌ Подключение '{name}' ({connector.db_type}) недоступно. Проверьте параметры."