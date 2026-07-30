from __future__ import annotations


class TestKnowledgeBase:
    def test_upsert_and_get_table(self, kb):
        kb.upsert_table("users", connection="pg1", description="Пользователи", owner="Ivan", layer="mart", is_certified=True)
        t = kb.get_table("users", "pg1")
        assert t is not None
        assert t["description"] == "Пользователи"
        assert t["owner"] == "Ivan"
        assert t["layer"] == "mart"
        assert t["is_certified"] == 1
        assert t["tags"] == []

    def test_get_table_returns_none_when_missing(self, kb):
        assert kb.get_table("nonexistent") is None

    def test_upsert_table_partial_update(self, kb):
        kb.upsert_table("orders", description="Заказы")
        kb.upsert_table("orders", owner="Petr")
        t = kb.get_table("orders")
        assert t["description"] == "Заказы"
        assert t["owner"] == "Petr"

    def test_all_tables(self, kb):
        kb.upsert_table("a")
        kb.upsert_table("b")
        names = {t["table_name"] for t in kb.all_tables()}
        assert {"a", "b"} <= names

    def test_upsert_and_get_columns(self, kb):
        kb.upsert_column("users", "email", description="почта", pii_type="email", is_sensitive=True)
        cols = kb.get_columns("users")
        assert len(cols) == 1
        assert cols[0]["column_name"] == "email"
        assert cols[0]["pii_type"] == "email"
        assert cols[0]["is_sensitive"] == 1

    def test_get_pii_columns(self, kb):
        kb.upsert_column("users", "id", source="schema")
        kb.upsert_column("users", "email", pii_type="email", is_sensitive=True)
        pii = kb.get_pii_columns("users")
        assert len(pii) == 1
        assert pii[0]["column_name"] == "email"

    def test_metrics_crud(self, kb):
        kb.upsert_metric("revenue", formula="SUM(amount)", description="выручка", owner="CFO")
        m = kb.get_metric("revenue")
        assert m["formula"] == "SUM(amount)"
        all_m = kb.all_metrics()
        assert any(x["name"] == "revenue" for x in all_m)
        assert kb.delete_metric("revenue") is True
        assert kb.get_metric("revenue") is None
        assert kb.delete_metric("revenue") is False

    def test_search_tables(self, kb):
        kb.upsert_table("users", description="Пользователи системы")
        kb.upsert_table("orders", description="Заказы клиентов")
        results = kb.search("Пользователи")
        assert any(r["table_name"] == "users" for r in results)

    def test_search_columns(self, kb):
        kb.upsert_column("users", "email", description="адрес почты")
        results = kb.search("почты")
        assert any(r.get("column_name") == "email" for r in results)

    def test_search_metrics(self, kb):
        kb.upsert_metric("revenue", formula="SUM(amount)", description="выручка в рублях")
        results = kb.search("выручка")
        assert any(r.get("name") == "revenue" for r in results)

    def test_search_empty_query(self, kb):
        kb.upsert_table("x")
        results = kb.search("")
        # LIKE '%%' — вернёт все
        assert isinstance(results, list)

    def test_search_limit(self, kb):
        for i in range(20):
            kb.upsert_table(f"t{i}", description=f"desc {i}")
        results = kb.search("desc", limit=5)
        assert len(results) <= 15  # 5 на каждую категорию (table/column/metric)

    def test_tags_persisted_as_json(self, kb):
        kb.upsert_table("x", tags=["prod", "pii"])
        t = kb.get_table("x")
        assert t["tags"] == ["prod", "pii"]


class TestLoggingDB:
    def test_log_query(self, log_db):
        log_db.log_query(tool="sql_query", sql="SELECT 1", table_name="t", rows_returned=5, duration_ms=12, success=True)
        logs = log_db.get_query_logs()
        assert len(logs) == 1
        assert logs[0]["tool"] == "sql_query"
        assert logs[0]["rows_returned"] == 5
        assert logs[0]["success"] == 1

    def test_log_query_failure(self, log_db):
        log_db.log_query(tool="sql_query", sql="DROP", success=False, error="blocked")
        logs = log_db.get_query_logs()
        assert logs[0]["success"] == 0
        assert "blocked" in logs[0]["error"]

    def test_log_error(self, log_db):
        log_db.log_error(error_type="SQL", message="syntax error", sql="SELECT", tool="sql_query")
        logs = log_db.get_error_logs()
        assert len(logs) == 1
        assert logs[0]["error_type"] == "SQL"

    def test_log_audit(self, log_db):
        log_db.log_audit(action="attach_database", target="pg1", details={"mode": "auto"})
        logs = log_db.get_audit_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "attach_database"
        assert "mode" in logs[0]["details"]

    def test_log_limit(self, log_db):
        for i in range(60):
            log_db.log_query(tool="t", sql=f"SELECT {i}")
        logs = log_db.get_query_logs(limit=10)
        assert len(logs) == 10


class TestExampleStore:
    def test_add_and_list(self):
        from app.services.example_store import get_example_store
        store = get_example_store()
        ex_id = store.add_example("сколько клиентов", "SELECT COUNT(*) FROM users", table_name="users")
        assert ex_id > 0
        all_ex = store.all_examples()
        assert any(e["query"] == "сколько клиентов" for e in all_ex)

    def test_get_by_table(self):
        from app.services.example_store import get_example_store
        store = get_example_store()
        store.add_example("q1", "SELECT 1", table_name="t1")
        store.add_example("q2", "SELECT 2", table_name="t2")
        t1 = store.get_by_table("t1")
        assert len(t1) == 1
        assert t1[0]["query"] == "q1"

    def test_is_golden_ordering(self):
        from app.services.example_store import get_example_store
        store = get_example_store()
        store.add_example("normal", "SELECT 1")
        store.add_example("golden", "SELECT 2", is_golden=True)
        all_ex = store.all_examples()
        # golden должен быть первым
        assert all_ex[0]["is_golden"] == 1

    def test_text_search_fallback(self):
        from app.services.example_store import get_example_store
        store = get_example_store()
        store.add_example("продажи по регионам", "SELECT region, SUM(amount) FROM sales GROUP BY region")
        store.add_example("топ клиентов", "SELECT name FROM clients ORDER BY amount DESC LIMIT 10")
        results = store._text_search("продажи регионов", top_k=2)
        assert len(results) >= 1
        assert "продажи" in results[0]["query"]