from __future__ import annotations

import json
from urllib.parse import urlencode


def build_superset_url(
    base_url: str,
    dashboard_id: str,
    params: dict | None = None,
) -> str:
    """Superset dashboard URL с предзаполненными фильтрами.

    params: {"region": "Москва", "date_from": "2024-01-01"}
    → https://superset.company.com/superset/dashboard/5/?fltr_col=region&fltr_val=Москва
    """
    url = f"{base_url.rstrip('/')}/superset/dashboard/{dashboard_id}/"
    if params:
        # Superset native filters API
        filter_parts = []
        for k, v in params.items():
            filter_parts.append(("fltr_col", k))
            filter_parts.append(("fltr_val", str(v)))
            filter_parts.append(("fltr_op", "in"))
        url += "?" + urlencode(filter_parts)
    return url


def build_grafana_url(
    base_url: str,
    dashboard_uid: str,
    params: dict | None = None,
    time_range: tuple[str, str] | None = None,
) -> str:
    """Grafana dashboard URL с переменными.

    params: {"region": "Москва"} → ?var-region=Москва
    time_range: ("2024-01-01", "2024-02-01") → &from=...&to=...
    """
    url = f"{base_url.rstrip('/')}/d/{dashboard_uid}"
    query_parts = []
    if params:
        for k, v in params.items():
            query_parts.append((f"var-{k}", str(v)))
    if time_range:
        query_parts.append(("from", time_range[0]))
        query_parts.append(("to", time_range[1]))
    if query_parts:
        url += "?" + urlencode(query_parts)
    return url


def build_datalens_url(
    base_url: str,
    chart_id: str,
    params: dict | None = None,
) -> str:
    """Yandex Datalens chart URL с фильтрами.

    params: {"region": "Москва"} → ?region=Москва
    """
    url = f"{base_url.rstrip('/')}/{chart_id}"
    if params:
        url += "?" + urlencode(params)
    return url


def build_bi_link(
    tool: str,
    base_url: str,
    dashboard_id: str = "",
    params: dict | None = None,
    time_range: tuple[str, str] | None = None,
) -> str:
    """Универсальный URL-билдер для BI-инструментов (ТЗ 3.4, v3)."""
    params = params or {}

    if tool == "superset":
        return build_superset_url(base_url, dashboard_id, params)
    elif tool == "grafana":
        return build_grafana_url(base_url, dashboard_id, params, time_range)
    elif tool == "datalens":
        return build_datalens_url(base_url, dashboard_id, params)
    elif tool == "tableau":
        # Tableau: base_url/views/workbook/sheet?:param1=val1
        url = f"{base_url.rstrip('/')}/views/{dashboard_id}"
        if params:
            tab_params = [f":{k}={v}" for k, v in params.items()]
            url += "?:embed=yes&" + "&".join(tab_params)
        return url
    elif tool == "powerbi":
        # Power BI: base_url/reportId?filter=Table/Column eq 'value'
        url = f"{base_url.rstrip('/')}/reportEmbed?reportId={dashboard_id}"
        if params:
            filter_parts = [f"Table/{k} eq '{v}'" for k, v in params.items()]
            url += "&filter=" + " and ".join(filter_parts)
        return url
    else:
        return f"{base_url}/{dashboard_id}"
