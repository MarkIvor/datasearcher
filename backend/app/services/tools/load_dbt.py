from __future__ import annotations

from app.config import settings
from app.session import Session
from .registry import register_tool


@register_tool(
    name="load_dbt",
    description="Импорт метаданных из dbt manifest.json (описания моделей, источники, тесты, владельцы, слои) в Knowledge Base. Обогащает анализ бизнес-контекстом.",
    parameters={
        "type": "object",
        "properties": {
            "manifest_path": {"type": "string", "description": "Путь к manifest.json (пусто = из настроек)"},
        },
    },
)
def load_dbt(session: Session, manifest_path: str = "") -> str:
    from ..dbt_loader import load_dbt_manifest

    path = manifest_path or settings.dbt_manifest_path
    if not path:
        return "Не указан путь к manifest.json. Передайте manifest_path или настройте DBT_MANIFEST_PATH."

    result = load_dbt_manifest(path)
    if "error" in result:
        return f"❌ {result['error']}"

    out = [
        "✅ dbt manifest загружен:",
        f"  Моделей: {result.get('models', 0)}",
        f"  Источников: {result.get('sources', 0)}",
        f"  Экспоузр: {result.get('exposures', 0)}",
        f"  Тестов: {result.get('tests', 0)}",
        f"  Описаний колонок: {result.get('columns', 0)}",
    ]
    return "\n".join(out)