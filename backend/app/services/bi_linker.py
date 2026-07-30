from __future__ import annotations

from urllib.parse import urlencode


def build_superset_url(
    base_url: str,
    dashboard_id: str,
    params: dict | None = None,
) -> str:
    url = f"{base_url.rstrip('/')}/superset/dashboard/{dashboard_id}/"
    if params:
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
    """Универсальный URL-билдер для BI-инструментов."""
    params = params or {}

    if tool == "superset":
        return build_superset_url(base_url, dashboard_id, params)
    elif tool == "grafana":
        return build_grafana_url(base_url, dashboard_id, params, time_range)
    elif tool == "datalens":
        return build_datalens_url(base_url, dashboard_id, params)
    elif tool == "tableau":
        url = f"{base_url.rstrip('/')}/views/{dashboard_id}"
        if params:
            tab_params = [f":{k}={v}" for k, v in params.items()]
            url += "?:embed=yes&" + "&".join(tab_params)
        return url
    elif tool == "powerbi":
        url = f"{base_url.rstrip('/')}/reportEmbed?reportId={dashboard_id}"
        if params:
            filter_parts = [f"Table/{k} eq '{v}'" for k, v in params.items()]
            url += "&filter=" + " and ".join(filter_parts)
        return url
    else:
        return f"{base_url}/{dashboard_id}"