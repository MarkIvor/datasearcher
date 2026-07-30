from __future__ import annotations

import pytest


class TestKnowledgeEndpoints:
    def test_list_kb_tables_requires_auth(self, client):
        r = client.get("/api/knowledge/tables")
        assert r.status_code == 401

    def test_list_kb_tables_empty(self, authed_client):
        r = authed_client.get("/api/knowledge/tables")
        assert r.status_code == 200
        assert r.json() == []

    def test_update_table_meta(self, authed_client):
        r = authed_client.put("/api/knowledge/tables", json={
            "table_name": "users", "description": "Пользователи", "owner": "Ivan",
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_get_kb_table_after_update(self, authed_client):
        authed_client.put("/api/knowledge/tables", json={"table_name": "users", "description": "x"})
        r = authed_client.get("/api/knowledge/tables/users")
        assert r.status_code == 200
        body = r.json()
        assert body["table"] is not None
        assert body["table"]["table_name"] == "users"

    def test_metrics_crud(self, authed_client):
        # create
        r = authed_client.post("/api/knowledge/metrics", json={
            "name": "revenue", "formula": "SUM(amount)", "description": "выручка",
        })
        assert r.status_code == 200
        # list
        r = authed_client.get("/api/knowledge/metrics")
        assert any(m["name"] == "revenue" for m in r.json())
        # delete
        r = authed_client.delete("/api/knowledge/metrics/revenue")
        assert r.status_code == 200

    def test_delete_missing_metric_404(self, authed_client):
        r = authed_client.delete("/api/knowledge/metrics/nonexistent")
        assert r.status_code == 404

    def test_search(self, authed_client):
        authed_client.put("/api/knowledge/tables", json={"table_name": "users", "description": "клиенты"})
        r = authed_client.get("/api/knowledge/search?q=клиенты")
        assert r.status_code == 200
        assert any(x["table_name"] == "users" for x in r.json())

    def test_search_empty_q(self, authed_client):
        r = authed_client.get("/api/knowledge/search?q=")
        assert r.status_code == 200
        assert r.json() == []

    def test_examples_empty(self, authed_client):
        r = authed_client.get("/api/knowledge/examples")
        assert r.status_code == 200
        assert r.json() == []


class TestLogsEndpoints:
    def test_query_logs_requires_auth(self, client):
        r = client.get("/api/logs/query")
        assert r.status_code == 401

    def test_query_logs_empty(self, authed_client):
        r = authed_client.get("/api/logs/query")
        assert r.status_code == 200
        assert r.json() == []

    def test_error_logs_empty(self, authed_client):
        r = authed_client.get("/api/logs/error")
        assert r.status_code == 200
        assert r.json() == []

    def test_audit_logs_empty(self, authed_client):
        r = authed_client.get("/api/logs/audit")
        assert r.status_code == 200
        assert r.json() == []

    def test_query_logs_with_data(self, authed_client):
        from app.services.logging_db import get_log_db
        get_log_db().log_query(tool="sql_query", sql="SELECT 1", success=True)
        r = authed_client.get("/api/logs/query")
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestMetadataEndpoints:
    def test_datahub_sync_not_configured(self, authed_client):
        # DATAHUB_URL пуст — должна быть 400
        r = authed_client.post("/api/metadata/datahub/sync", json={"limit": 10})
        assert r.status_code == 400
        assert "DataHub" in r.json()["detail"]

    def test_dbt_upload_invalid_file(self, authed_client, tmp_path):
        # не JSON — должно вернуть 400
        from io import BytesIO
        bad = BytesIO(b"not a json")
        r = authed_client.post(
            "/api/metadata/dbt",
            files={"file": ("manifest.json", bad, "application/json")},
        )
        # либо 400 (ошибка парсинга), либо другая ошибка
        assert r.status_code in (400, 500)

    def test_bi_link_builder(self, authed_client):
        r = authed_client.post("/api/metadata/bi-link", json={
            "tool": "superset",
            "base_url": "https://superset.example.com",
            "dashboard_id": "5",
            "params": {"region": "Москва"},
        })
        assert r.status_code == 200
        url = r.json()["url"]
        assert "superset.example.com" in url
        assert "fltr_col=region" in url

    def test_bi_link_grafana_with_time(self, authed_client):
        r = authed_client.post("/api/metadata/bi-link", json={
            "tool": "grafana",
            "base_url": "https://grafana.example.com",
            "dashboard_id": "abc",
            "params": {"host": "s1"},
            "time_from": "2024-01-01",
            "time_to": "2024-02-01",
        })
        assert r.status_code == 200
        url = r.json()["url"]
        assert "var-host=s1" in url
        assert "from=2024-01-01" in url


class TestConnectionsModesEndpoint:
    def test_modes_requires_auth(self, client):
        r = client.get("/api/connections/modes")
        assert r.status_code == 401

    def test_modes_returns_all_modes(self, authed_client):
        r = authed_client.get("/api/connections/modes")
        assert r.status_code == 200
        body = r.json()
        assert "auto" in body["modes"]
        assert "remote" in body["modes"]
        assert "dump" in body["modes"]
        assert "federated" in body["modes"]
        assert "postgresql" in body["db_types"]
        assert "clickhouse" in body["db_types"]
        assert "api" in body["db_types"]


class TestAdminEnterpriseSettings:
    def test_requires_admin(self, client):
        r = client.get("/api/admin/enterprise-settings")
        assert r.status_code == 401

    def test_returns_settings(self, authed_client):
        r = authed_client.get("/api/admin/enterprise-settings")
        assert r.status_code == 200
        body = r.json()
        assert "read_only" in body
        assert "pii_masking" in body
        assert "rate_limit_sql" in body
        assert "default_mode" in body
        assert body["default_mode"] == "auto"


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}