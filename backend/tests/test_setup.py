from __future__ import annotations

import pytest


class TestSetupAuth:
    def test_get_setup_requires_auth(self, client):
        r = client.get("/api/setup/")
        assert r.status_code == 401

    def test_update_setup_requires_auth(self, client):
        r = client.put("/api/setup/", json={"step": 1})
        assert r.status_code == 401

    def test_mcp_config_requires_auth(self, client):
        r = client.post("/api/setup/mcp-config", json={})
        assert r.status_code == 401

    def test_test_llm_requires_auth(self, client):
        r = client.post("/api/setup/test-llm", json={})
        assert r.status_code == 401


class TestSetupState:
    def test_initial_state(self, authed_client):
        r = authed_client.get("/api/setup/")
        assert r.status_code == 200
        body = r.json()
        assert body["completed"] is False
        assert body["step"] == 1
        assert body["steps_total"] == 4
        assert body["is_admin"] is True
        assert body["mode"] == ""
        assert "enterprise" in body
        assert "read_only" in body["enterprise"]
        assert "default_mode" in body["enterprise"]

    def test_step_validation(self, authed_client):
        r = authed_client.put("/api/setup/", json={"step": 0})
        assert r.status_code == 400
        r = authed_client.put("/api/setup/", json={"step": 99})
        assert r.status_code == 400

    def test_save_step_and_mode(self, authed_client):
        r = authed_client.put("/api/setup/", json={"step": 2, "mode": "interface"})
        assert r.status_code == 200
        body = r.json()
        assert body["step"] == 2
        assert body["mode"] == "interface"
        assert body["completed"] is False

        r = authed_client.get("/api/setup/")
        assert r.json()["step"] == 2
        assert r.json()["mode"] == "interface"

    def test_invalid_mode_rejected(self, authed_client):
        r = authed_client.put("/api/setup/", json={"mode": "browser"})
        assert r.status_code == 400

    def test_mcp_mode_saved(self, authed_client):
        r = authed_client.put("/api/setup/", json={"mode": "mcp"})
        assert r.status_code == 200
        assert r.json()["mode"] == "mcp"

    def test_complete_setup(self, authed_client):
        r = authed_client.put("/api/setup/", json={"completed": True, "mode": "mcp"})
        assert r.status_code == 200
        assert r.json()["completed"] is True
        r = authed_client.get("/api/setup/")
        assert r.json()["completed"] is True

    def test_uncomplete_setup(self, authed_client):
        authed_client.put("/api/setup/", json={"completed": True})
        r = authed_client.put("/api/setup/", json={"completed": False})
        assert r.status_code == 200
        assert r.json()["completed"] is False

    def test_llm_params_saved(self, authed_client):
        r = authed_client.put("/api/setup/", json={
            "llm_url": "http://localhost:11434/v1/",
            "llm_model": "qwen2.5:14b",
            "llm_api_key": "sk-test-key-1234567890",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["llm"]["url"] == "http://localhost:11434/v1"
        assert body["llm"]["model"] == "qwen2.5:14b"
        assert body["llm"]["api_key_masked"].endswith("...")
        assert body["llm"]["has_key"] is True

    def test_llm_masked_key_keeps_existing(self, authed_client):
        authed_client.put("/api/setup/", json={
            "llm_url": "http://localhost:11434/v1",
            "llm_api_key": "sk-real-secret-key-value",
        })
        r = authed_client.put("/api/setup/", json={
            "llm_url": "http://other:8000/v1",
            "llm_api_key": "sk-real-s...",
        })
        assert r.status_code == 200
        assert r.json()["llm"]["url"] == "http://other:8000/v1"


class TestSetupScope:
    def test_non_admin_cannot_set_global(self, client):
        from app.services.auth_service import create_access_token

        r = client.post("/api/auth/register", json={
            "email": "user1@test-ds.com",
            "password": "pass12345",
            "display_name": "User One",
        })
        assert r.status_code == 200, r.text
        uid = r.json()["user"]["id"]
        client.cookies.set("access_token", create_access_token(uid, "analyst"))

        r = client.put("/api/setup/", json={"scope": "global", "completed": True, "mode": "interface"})
        assert r.status_code == 200
        body = r.json()
        # scope принудительно user для не-админа
        assert body["completed"] is True
        assert body["scope"] == "user"

        # новый пользователь не должен видеть глобально завершённый сетап
        r = client.post("/api/auth/register", json={
            "email": "user2@test-ds.com",
            "password": "pass12345",
            "display_name": "User Two",
        })
        assert r.status_code == 200, r.text
        uid2 = r.json()["user"]["id"]
        client.cookies.set("access_token", create_access_token(uid2, "analyst"))

        r = client.get("/api/setup/")
        assert r.status_code == 200
        assert r.json()["completed"] is False

    def test_admin_global_scope_visible_to_new_users(self, authed_client, client):
        r = authed_client.put("/api/setup/", json={"scope": "global", "mode": "mcp", "completed": True})
        assert r.status_code == 200

        # новый пользователь должен увидеть глобально завершённый сетап
        r = client.post("/api/auth/register", json={
            "email": "newbie@test-ds.com",
            "password": "pass12345",
            "display_name": "Newbie",
        })
        assert r.status_code == 200, r.text
        from app.services.auth_service import create_access_token
        uid = r.json()["user"]["id"]
        client.cookies.set("access_token", create_access_token(uid, "analyst"))

        r = client.get("/api/setup/")
        assert r.status_code == 200
        body = r.json()
        assert body["completed"] is True
        assert body["mode"] == "mcp"


class TestMcpConfig:
    def test_no_connections_400(self, authed_client):
        r = authed_client.post("/api/setup/mcp-config", json={})
        assert r.status_code == 400

    def test_generate_from_postgres_connection(self, authed_client):
        r = authed_client.post("/api/connections/", json={
            "name": "main_pg",
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "ecommerce",
            "username": "datasearcher",
            "password": "ds_demo_pass_2024",
        })
        assert r.status_code == 200

        r = authed_client.post("/api/setup/mcp-config", json={})
        assert r.status_code == 200
        body = r.json()
        assert "main_pg" in body["connections"]
        assert 'db_type: postgresql' in body["connections_yaml"]
        assert 'host: "localhost"' in body["connections_yaml"]
        assert 'port: 5432' in body["connections_yaml"]
        assert 'database: "ecommerce"' in body["connections_yaml"]
        assert 'mode: auto' in body["connections_yaml"]
        assert '"datasearcher-mcp"' in body["claude_json"]
        assert "mcpServers" in body["claude_json"]
        assert "cursor_json" in body
        assert "--transport http" in body["http_command"]
        assert "docker" in body["docker_command"]

    def test_generate_mysql_and_sqlite(self, authed_client):
        authed_client.post("/api/connections/", json={
            "name": "crm_mysql", "db_type": "mysql",
            "host": "localhost", "port": 3306, "database": "crm",
            "username": "datasearcher", "password": "pass",
        })
        authed_client.post("/api/connections/", json={
            "name": "local_sqlite", "db_type": "sqlite", "database": "mydb.db",
        })
        r = authed_client.post("/api/setup/mcp-config", json={})
        assert r.status_code == 200
        y = r.json()["connections_yaml"]
        assert "db_type: mysql" in y
        assert "db_type: sqlite" in y
        assert "database: \"mydb.db\"" in y

    def test_filter_by_connection_ids(self, authed_client):
        r1 = authed_client.post("/api/connections/", json={
            "name": "conn_a", "db_type": "sqlite", "database": "a.db",
        })
        r2 = authed_client.post("/api/connections/", json={
            "name": "conn_b", "db_type": "sqlite", "database": "b.db",
        })
        id_a = r1.json()["id"]
        id_b = r2.json()["id"]

        r = authed_client.post("/api/setup/mcp-config", json={"connection_ids": [id_b]})
        assert r.status_code == 200
        body = r.json()
        assert body["connections"] == ["conn_b"]
        assert "conn_b" in body["connections_yaml"]
        assert "conn_a" not in body["connections_yaml"]

    def test_yaml_name_quoting(self, authed_client):
        authed_client.post("/api/connections/", json={
            "name": 'db "prod"', "db_type": "sqlite", "database": "p.db",
        })
        r = authed_client.post("/api/setup/mcp-config", json={})
        assert r.status_code == 200
        assert 'name: "db \\"prod\\""' in r.json()["connections_yaml"]


class TestTestLLM:
    def test_test_llm_bad_url(self, authed_client):
        r = authed_client.post("/api/setup/test-llm", json={"url": "http://127.0.0.1:1/v1"})
        assert r.status_code == 200
        body = r.json()
        assert body["connected"] is False
        assert "error" in body

    def test_test_llm_empty_url_uses_saved(self, authed_client):
        authed_client.put("/api/setup/", json={"llm_url": "http://127.0.0.1:2/v1"})
        r = authed_client.post("/api/setup/test-llm", json={})
        assert r.status_code == 200
        assert r.json()["connected"] is False
