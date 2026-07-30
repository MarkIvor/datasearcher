from __future__ import annotations

import json

from app.session import Session
from .registry import register_tool


@register_tool(
    name="build_bi_link",
    description="Сгенерировать URL для BI-инструмента (Superset, Grafana, Yandex Datalens, Tableau, Power BI) с предзаполненными фильтрами.",
    parameters={
        "type": "object",
        "properties": {
            "tool": {"type": "string", "description": "BI-инструмент: superset | grafana | datalens | tableau | powerbi"},
            "base_url": {"type": "string", "description": "Базовый URL BI-системы"},
            "dashboard_id": {"type": "string", "description": "ID дашборда/чарта"},
            "params": {"type": "string", "description": "JSON с фильтрами: {\"region\": \"Москва\"}"},
            "time_from": {"type": "string", "description": "Начало периода (для grafana)"},
            "time_to": {"type": "string", "description": "Конец периода (для grafana)"},
        },
        "required": ["tool", "base_url"],
    },
)
def build_bi_link(
    session: Session,
    tool: str,
    base_url: str,
    dashboard_id: str = "",
    params: str = "",
    time_from: str = "",
    time_to: str = "",
) -> str:
    from ..bi_linker import build_bi_link as _build

    params_dict: dict = {}
    if params:
        try:
            params_dict = json.loads(params)
        except json.JSONDecodeError:
            return f"❌ params должен быть валидным JSON. Получено: {params}"

    time_range = None
    if time_from and time_to:
        time_range = (time_from, time_to)

    url = _build(
        tool=tool,
        base_url=base_url,
        dashboard_id=dashboard_id,
        params=params_dict,
        time_range=time_range,
    )
    return f"🔗 BI-ссылка ({tool}):\n\n{url}"