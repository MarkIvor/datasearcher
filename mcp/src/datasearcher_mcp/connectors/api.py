from __future__ import annotations

import json
from typing import Any

import httpx

from .base import Connector


class ApiConnector(Connector):
    """REST API коннектор: данные из HTTP-эндпоинтов → DuckDB (ТЗ + v3.1).

    Конфигурация в connections.yaml:
        db_type: api
        base_url: https://api.company.com/v1
        auth_header: "Authorization: Bearer ${API_TOKEN}"
        endpoints:
          - path: /customers
            table_name: customers
            params: "limit=1000"
          - path: /orders
            table_name: orders
            params: "status=active&limit=5000"
        pagination: offset  # offset | cursor | none
        mode: dump           # выгрузить в DuckDB при старте
    """

    db_type = "api"

    def __init__(self, name: str, params: dict):
        self.name = name
        self.params = params
        self._base_url = params.get("base_url", "").rstrip("/")
        self._auth_header = params.get("auth_header", "")
        self._extra_headers = params.get("headers", {})
        self._endpoints = params.get("endpoints", [])
        self._pagination = params.get("pagination", "none")
        self._page_size = int(params.get("page_size", 1000))
        self._max_pages = int(params.get("max_pages", 100))

    def _headers(self) -> dict:
        h = {"Accept": "application/json"}
        if self._auth_header:
            # Подстановка env vars
            header_val = self._auth_header
            import re, os
            header_val = re.sub(
                r"\$\{(\w+)\}",
                lambda m: os.environ.get(m.group(1), ""),
                header_val,
            )
            # auth_header может быть "Authorization: Bearer xxx"
            if ":" in header_val:
                key, val = header_val.split(":", 1)
                h[key.strip()] = val.strip()
            else:
                h["Authorization"] = header_val
        h.update(self._extra_headers)
        return h

    def test(self) -> bool:
        if not self._endpoints:
            return False
        try:
            ep = self._endpoints[0]
            url = self._base_url + ep.get("path", "")
            with httpx.Client(timeout=10) as client:
                resp = client.get(url, headers=self._headers())
            return resp.status_code < 400
        except Exception:
            return False

    def list_tables(self) -> list[str]:
        """Таблицы = имена из endpoints config."""
        return [ep.get("table_name", ep.get("path", "").strip("/")) for ep in self._endpoints]

    def fetch_table(self, table: str, limit: int = 50000) -> tuple[list[str], list[tuple]]:
        """Выгрузка данных из REST API → flatten → (columns, rows)."""
        ep = self._find_endpoint(table)
        if not ep:
            raise ValueError(f"Endpoint для таблицы '{table}' не найден в конфиге")

        path = ep.get("path", "")
        params = ep.get("params", "")
        url = self._base_url + path

        # Пагинация
        all_data: list[dict] = []
        page = 0

        while page < self._max_pages and len(all_data) < limit:
            page_params = {}
            if params:
                for kv in params.split("&"):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        page_params[k] = v

            if self._pagination == "offset":
                page_params["offset"] = page * self._page_size
                page_params["limit"] = self._page_size
            elif self._pagination == "cursor" and page > 0:
                if not all_data:
                    break
                # cursor из последнего элемента (зависит от API)
                last = all_data[-1]
                if "cursor" in last:
                    page_params["cursor"] = last["cursor"]

            try:
                with httpx.Client(timeout=30) as client:
                    resp = client.get(url, params=page_params, headers=self._headers())
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as e:
                break

            # Normalize response: может быть list, {data: [...]}, {results: [...]}
            items = _extract_items(data)
            if not items:
                break

            all_data.extend(items)

            # Если пришло меньше, чем page_size — это последняя страница
            if len(items) < self._page_size:
                break

            if self._pagination == "none":
                break

            page += 1

        all_data = all_data[:limit]

        if not all_data:
            return [], []

        # Flatten: из dict → columns + rows
        cols, rows = _flatten_records(all_data)
        return cols, rows

    def row_count(self, table: str) -> int:
        """Приблизительный row_count через 1 запись."""
        try:
            cols, rows = self.fetch_table(table, limit=1)
            return len(rows)
        except Exception:
            return 0

    def describe(self, table: str) -> list[dict]:
        """Описание колонок из первой записи."""
        try:
            cols, rows = self.fetch_table(table, limit=1)
            return [{"name": c, "type": "unknown"} for c in cols]
        except Exception:
            return []

    def execute_sql(self, sql: str) -> tuple[list[str], list[tuple]]:
        raise NotImplementedError("API connector не поддерживает execute_sql (push-down). Используйте dump-режим.")

    def _find_endpoint(self, table_name: str) -> dict | None:
        for ep in self._endpoints:
            if ep.get("table_name") == table_name:
                return ep
            # fallback: table_name = path без /
            path = ep.get("path", "").strip("/")
            if path == table_name:
                return ep
        return None


def _extract_items(data: Any) -> list[dict]:
    """Извлечь список записей из разных форматов API-ответа."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "results", "items", "records", "rows"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Если dict без известного ключа — возможно это одна запись
        return [data]
    return []


def _flatten_records(records: list[dict]) -> tuple[list[str], list[tuple]]:
    """Flatten list[dict] → (columns, rows).

    Поддерживает dot-notation для вложенных объектов:
    {"user": {"name": "Anna"}} → column "user.name" = "Anna"
    """
    # Собираем все ключи
    all_keys: set[str] = set()
    for rec in records:
        all_keys.update(_flatten_keys(rec))

    cols = sorted(all_keys)
    rows = []
    for rec in records:
        flat = _flatten_dict(rec)
        row = tuple(flat.get(c) for c in cols)
        rows.append(row)

    return cols, rows


def _flatten_keys(d: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for k, v in d.items():
        full_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            keys.update(_flatten_keys(v, full_key))
        else:
            keys.add(full_key)
    return keys


def _flatten_dict(d: dict, prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in d.items():
        full_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            result.update(_flatten_dict(v, full_key))
        elif isinstance(v, list):
            result[full_key] = json.dumps(v, ensure_ascii=False)
        else:
            result[full_key] = v
    return result
