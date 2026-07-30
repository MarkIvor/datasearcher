from __future__ import annotations

import json
import os
from typing import Any

from .knowledge_base import get_kb


def load_dbt_manifest(manifest_path: str) -> dict:
    """Загрузить и распарсить dbt manifest.json.

    Извлекает:
    - models: description, meta (owner, tags), materialized, columns
    - sources: description, columns
    - exposures: description, type
    - tests: not_null, unique, accepted_values

    Обогащает KnowledgeBase.
    """
    if not os.path.isfile(manifest_path):
        return {"error": f"manifest.json не найден: {manifest_path}"}

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return {"error": f"manifest.json не валидный JSON: {e}"}
    except Exception as e:
        return {"error": f"не удалось прочитать manifest.json: {e}"}

    stats = {"models": 0, "sources": 0, "exposures": 0, "tests": 0, "columns": 0}
    kb = get_kb()

    for node_id, node in manifest.get("nodes", {}).items():
        if not node_id.startswith("model."):
            continue
        resource_type = node.get("resource_type", "")
        if resource_type != "model":
            continue

        name = node.get("name", "")
        description = node.get("description", "")
        meta = node.get("meta", {})
        owner = meta.get("owner", "")
        tags = node.get("tags", [])
        schema = node.get("schema", "")

        layer = _detect_layer(name, node.get("original_file_path", ""))

        kb.upsert_table(
            table_name=name,
            connection=f"dbt:{schema}",
            description=description or None,
            owner=owner or None,
            layer=layer,
            tags=tags if tags else None,
            is_certified=layer == "mart",
            source="dbt",
        )
        stats["models"] += 1

        for col_name, col_info in node.get("columns", {}).items():
            col_desc = col_info.get("description", "")
            meta_c = col_info.get("meta", {})
            if col_desc or meta_c:
                kb.upsert_column(
                    table_name=name,
                    column_name=col_name,
                    description=col_desc or None,
                    source="dbt",
                )
                stats["columns"] += 1

    for src_id, src in manifest.get("sources", {}).items():
        name = src.get("name", "")
        description = src.get("description", "")
        source_name = src.get("source_name", "")

        kb.upsert_table(
            table_name=name,
            connection=f"dbt_source:{source_name}",
            description=description or None,
            layer="raw",
            source="dbt",
        )
        stats["sources"] += 1

        for col_name, col_info in src.get("columns", {}).items():
            col_desc = col_info.get("description", "")
            if col_desc:
                kb.upsert_column(
                    table_name=name,
                    column_name=col_name,
                    description=col_desc,
                    source="dbt",
                )
                stats["columns"] += 1

    for exp_id, exp in manifest.get("exposures", {}).items():
        name = exp.get("name", "")
        description = exp.get("description", "")
        exp_type = exp.get("type", "")
        kb.upsert_table(
            table_name=f"exposure_{name}",
            connection="dbt_exposure",
            description=description or None,
            layer="exposure",
            tags=[exp_type] if exp_type else None,
            source="dbt",
        )
        stats["exposures"] += 1

    for test_id, test in manifest.get("nodes", {}).items():
        if not test_id.startswith("test."):
            continue
        stats["tests"] += 1

    return {"success": True, **stats}


def load_dbt_semantic_models(yml_path: str) -> dict:
    """Парсинг semantic_models.yml → метрики в KB."""
    import yaml

    if not os.path.isfile(yml_path):
        return {"error": f"Файл не найден: {yml_path}"}

    with open(yml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    kb = get_kb()
    count = 0

    for sm in data.get("semantic_models", []):
        for metric in sm.get("metrics", []):
            name = metric.get("name", "")
            formula = metric.get("expression", "")
            description = metric.get("description", "")
            kb.upsert_metric(name, formula, description)
            count += 1

    return {"success": True, "metrics_loaded": count}


def _detect_layer(name: str, file_path: str) -> str:
    name_lower = name.lower()
    path_lower = file_path.lower()

    if name_lower.startswith("stg_") or "staging" in path_lower:
        return "staging"
    if name_lower.startswith("int_") or "intermediate" in path_lower:
        return "intermediate"
    if name_lower.startswith("fct_") or "mart" in path_lower or "marts" in path_lower:
        return "mart"
    if name_lower.startswith("dim_"):
        return "mart"
    return ""