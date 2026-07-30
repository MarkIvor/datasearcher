from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.dbt_loader import load_dbt_manifest, load_dbt_semantic_models, _detect_layer


class TestDetectLayer:
    def test_staging_by_name(self):
        assert _detect_layer("stg_users", "") == "staging"

    def test_staging_by_path(self):
        assert _detect_layer("x", "models/staging/users.sql") == "staging"

    def test_intermediate_by_name(self):
        assert _detect_layer("int_orders", "") == "intermediate"

    def test_mart_by_name_fct(self):
        assert _detect_layer("fct_orders", "") == "mart"

    def test_mart_by_name_dim(self):
        assert _detect_layer("dim_users", "") == "mart"

    def test_mart_by_path(self):
        assert _detect_layer("x", "models/marts/sales.sql") == "mart"

    def test_unknown_returns_empty(self):
        assert _detect_layer("random_table", "models/random.sql") == ""


class TestLoadDbtManifest:
    def _manifest(self) -> dict:
        return {
            "nodes": {
                "model.project.stg_users": {
                    "resource_type": "model",
                    "name": "stg_users",
                    "description": "Staging users",
                    "meta": {"owner": "data-team"},
                    "tags": ["staging", "pii"],
                    "config": {"materialized": "view"},
                    "schema": "analytics",
                    "database": "db",
                    "original_file_path": "models/staging/stg_users.sql",
                    "columns": {
                        "user_id": {"description": "ID пользователя", "meta": {}},
                        "email": {"description": "Email адрес", "meta": {}},
                    },
                },
                "model.project.fct_orders": {
                    "resource_type": "model",
                    "name": "fct_orders",
                    "description": "Fact orders table",
                    "meta": {"owner": "sales-team"},
                    "tags": ["mart"],
                    "config": {"materialized": "table"},
                    "schema": "marts",
                    "database": "db",
                    "original_file_path": "models/marts/fct_orders.sql",
                    "columns": {},
                },
                "test.project.unique_stg_users_user_id": {
                    "resource_type": "test",
                    "name": "unique_stg_users_user_id",
                },
            },
            "sources": {
                "source.project.raw.users": {
                    "name": "users",
                    "description": "Raw users source",
                    "schema": "raw",
                    "source_name": "raw",
                    "columns": {"id": {"description": "PK"}},
                },
            },
            "exposures": {
                "exposure.project.sales_dashboard": {
                    "name": "sales_dashboard",
                    "description": "Sales BI dashboard",
                    "type": "dashboard",
                },
            },
        }

    def test_file_not_found(self):
        result = load_dbt_manifest("/nonexistent/manifest.json")
        assert "error" in result
        assert "не найден" in result["error"]

    def test_load_success(self, kb, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(self._manifest()), encoding="utf-8")
        result = load_dbt_manifest(str(p))
        assert result.get("success") is True
        assert result["models"] == 2
        assert result["sources"] == 1
        assert result["exposures"] == 1
        assert result["tests"] == 1
        assert result["columns"] == 3  # 2 + 1

    def test_enriches_kb(self, kb, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(self._manifest()), encoding="utf-8")
        load_dbt_manifest(str(p))
        # проверим что stg_users записан
        t = kb.get_table("stg_users", connection="dbt:analytics")
        assert t is not None
        assert t["description"] == "Staging users"
        assert t["owner"] == "data-team"
        assert t["layer"] == "staging"
        assert t["is_certified"] == 0  # не mart

    def test_mart_is_certified(self, kb, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(self._manifest()), encoding="utf-8")
        load_dbt_manifest(str(p))
        t = kb.get_table("fct_orders", connection="dbt:marts")
        assert t["layer"] == "mart"
        assert t["is_certified"] == 1

    def test_columns_loaded(self, kb, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(self._manifest()), encoding="utf-8")
        load_dbt_manifest(str(p))
        c = kb.get_column("stg_users", "user_id")
        assert c["description"] == "ID пользователя"
        c = kb.get_column("stg_users", "email")
        assert c["description"] == "Email адрес"

    def test_sources_loaded(self, kb, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(self._manifest()), encoding="utf-8")
        load_dbt_manifest(str(p))
        t = kb.get_table("users", connection="dbt_source:raw")
        assert t["layer"] == "raw"

    def test_exposures_loaded(self, kb, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps(self._manifest()), encoding="utf-8")
        load_dbt_manifest(str(p))
        t = kb.get_table("exposure_sales_dashboard", connection="dbt_exposure")
        assert t["layer"] == "exposure"
        assert "dashboard" in t["tags"]

    def test_invalid_json_returns_error(self, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text("not a json {{{", encoding="utf-8")
        result = load_dbt_manifest(str(p))
        assert "error" in result
        assert "JSON" in result["error"]


class TestLoadDbtSemanticModels:
    def test_file_not_found(self):
        result = load_dbt_semantic_models("/nonexistent.yml")
        assert "error" in result

    def test_load_metrics(self, kb, tmp_path):
        p = tmp_path / "semantic.yml"
        p.write_text(
            "semantic_models:\n"
            "  - name: sales\n"
            "    metrics:\n"
            "      - name: revenue\n"
            "        expression: SUM(amount)\n"
            "        description: Total revenue\n"
            "      - name: order_count\n"
            "        expression: COUNT(*)\n"
            "        description: Number of orders\n",
            encoding="utf-8",
        )
        result = load_dbt_semantic_models(str(p))
        assert result.get("success") is True
        assert result["metrics_loaded"] == 2
        m = kb.get_metric("revenue")
        assert m["formula"] == "SUM(amount)"

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.yml"
        p.write_text("", encoding="utf-8")
        result = load_dbt_semantic_models(str(p))
        assert result.get("success") is True
        assert result["metrics_loaded"] == 0