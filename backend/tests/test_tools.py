from __future__ import annotations

import json
import os

import pytest

from app.services.tools.registry import get_tool_handler, get_tool_definitions


class TestToolRegistry:
    def test_46_tools_registered(self):
        defs = get_tool_definitions()
        assert len(defs) == 46, f"Expected 46 tools, got {len(defs)}"

    def test_all_handlers_present(self):
        from app.services.tools.registry import TOOL_DEFINITIONS, TOOL_HANDLERS
        missing = [d["function"]["name"] for d in TOOL_DEFINITIONS if d["function"]["name"] not in TOOL_HANDLERS]
        assert missing == []

    def test_each_tool_has_required_fields(self):
        for d in get_tool_definitions():
            fn = d["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"

    def test_handler_returns_callable(self):
        for d in get_tool_definitions():
            h = get_tool_handler(d["function"]["name"])
            assert callable(h), f"{d['function']['name']} handler not callable"

    @pytest.mark.parametrize("name", [
        "sql_query", "query_explain", "get_schema", "attach_database", "refresh_schema",
        "test_connection", "load_file", "profile_data", "smart_summary", "data_quality_report",
        "find_duplicates", "detect_anomalies", "sample_data", "correlation_analysis",
        "distribution_analysis", "cross_tab", "pivot_table", "segment_data", "compare_tables",
        "time_analysis", "auto_insights", "generate_sql", "visualize_data", "predict_trend",
        "cluster_analysis", "feature_importance", "statistical_test", "classify_rows",
        "transform_data", "merge_tables", "export_data", "export_xlsx", "detect_patterns",
        "build_dashboard", "data_story", "create_public_dashboard", "scan_pii",
        "get_logs", "add_example", "search_knowledge", "load_dbt", "sync_datahub",
        "list_metrics", "update_metadata", "build_bi_link", "semantic_search",
    ])
    def test_tool_present(self, name):
        assert get_tool_handler(name) is not None, f"Tool {name} missing"


class TestSqlQueryTool:
    def test_basic_select(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="SELECT COUNT(*) AS n FROM sample")
        assert "1" in result  # одна строка
        assert "n" in result

    def test_select_with_filter(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="SELECT name FROM sample WHERE region='Москва'")
        assert "Анна" in result
        assert "Вика" in result

    def test_readonly_blocks_drop(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="DROP TABLE sample")
        assert "Read-only" in result or "заблокирован" in result

    def test_readonly_blocks_delete(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="DELETE FROM sample WHERE id=1")
        assert "Read-only" in result or "заблокирован" in result

    def test_sql_error_handled(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="SELECT * FROM nonexistent_table")
        assert "не найдена" in result.lower() or "❌" in result or "error" in result.lower()

    def test_json_format(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="SELECT 1 AS x", format="json")
        parsed = json.loads(result)
        assert "columns" in parsed
        assert parsed["rows"][0][0] == 1

    def test_csv_format(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="SELECT 1 AS x", format="csv")
        assert "x" in result
        assert "1" in result

    def test_pii_masking_in_sql_result(self, loaded_session):
        session, _, _ = loaded_session
        # Пометим email как PII в KB
        from app.services.knowledge_base import get_kb
        get_kb().upsert_column("sample", "email", pii_type="email", is_sensitive=True, source="test")
        handler = get_tool_handler("sql_query")
        result = handler(session, sql="SELECT email FROM sample LIMIT 1")
        # email должен быть замаскирован
        assert "***@" in result


class TestGetSchemaTool:
    def test_returns_schema(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("get_schema")
        result = handler(session, table_name="sample")
        assert "sample" in result
        assert "Строк" in result
        assert "email" in result
        assert "amount" in result

    def test_missing_table_error(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("get_schema")
        result = handler(session, table_name="nonexistent")
        assert "не найдена" in result.lower()


class TestScanPiiTool:
    def test_scan_finds_email(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("scan_pii")
        result = handler(session, table_name="sample")
        # email-колонка должна детектиться
        assert "email" in result.lower() or "PII" in result

    def test_scan_missing_table(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("scan_pii")
        result = handler(session, table_name="nonexistent")
        assert "не найдена" in result.lower() or "ошибка" in result.lower()


class TestGetLogsTool:
    def test_query_logs(self, loaded_session, log_db):
        session, _, _ = loaded_session
        log_db.log_query(tool="sql_query", sql="SELECT 1", success=True)
        handler = get_tool_handler("get_logs")
        result = handler(session, log_type="query", limit=5)
        assert "sql_query" in result

    def test_error_logs_empty(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("get_logs")
        result = handler(session, log_type="error")
        assert "пусты" in result

    def test_audit_logs(self, loaded_session, log_db):
        session, _, _ = loaded_session
        log_db.log_audit(action="test_action", target="x")
        handler = get_tool_handler("get_logs")
        result = handler(session, log_type="audit")
        assert "test_action" in result


class TestExportXlsxTool:
    def test_export_creates_xlsx(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("export_xlsx")
        result = handler(session, table_name="sample")
        assert "__EXPORT_DATA__" in result
        assert "format=xlsx" in result
        assert "filename=" in result

    def test_export_missing_table(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("export_xlsx")
        result = handler(session, table_name="nonexistent")
        assert "Ошибка" in result or "нет" in result.lower()


class TestListMetricsTool:
    def test_empty_metrics(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("list_metrics")
        result = handler(session)
        assert "нет" in result.lower() or "не" in result.lower()

    def test_with_metrics(self, loaded_session, kb):
        session, _, _ = loaded_session
        kb.upsert_metric("revenue", formula="SUM(amount)", description="выручка")
        handler = get_tool_handler("list_metrics")
        result = handler(session)
        assert "revenue" in result


class TestUpdateMetadataTool:
    def test_update_table_description(self, loaded_session, kb):
        session, _, _ = loaded_session
        handler = get_tool_handler("update_metadata")
        result = handler(session, table_name="sample", description="Тестовая таблица", owner="Ivan")
        assert "обновлены" in result
        t = kb.get_table("sample")
        assert t["description"] == "Тестовая таблица"
        assert t["owner"] == "Ivan"

    def test_update_column_descriptions(self, loaded_session, kb):
        session, _, _ = loaded_session
        handler = get_tool_handler("update_metadata")
        cols_json = json.dumps({"email": "адрес почты", "amount": "сумма заказа"})
        handler(session, table_name="sample", column_descriptions=cols_json)
        c = kb.get_column("sample", "email")
        assert c["description"] == "адрес почты"


class TestBuildBiLinkTool:
    def test_superset_link(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("build_bi_link")
        result = handler(
            session, tool="superset", base_url="https://superset.example.com",
            dashboard_id="5", params='{"region": "Москва"}',
        )
        assert "superset.example.com" in result
        assert "5" in result

    def test_grafana_link_with_time(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("build_bi_link")
        result = handler(
            session, tool="grafana", base_url="https://grafana.example.com",
            dashboard_id="abc", params='{"host": "server1"}',
            time_from="2024-01-01", time_to="2024-02-01",
        )
        assert "grafana.example.com" in result
        assert "from=2024-01-01" in result

    def test_invalid_params_json(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("build_bi_link")
        result = handler(
            session, tool="superset", base_url="https://x.com",
            params="not-json{",
        )
        assert "JSON" in result or "json" in result


class TestAddExampleTool:
    def test_add_example(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("add_example")
        result = handler(session, query="сколько клиентов", sql="SELECT COUNT(*) FROM users", is_golden=True)
        assert "добавлен" in result
        assert "golden" in result.lower() or "⭐" in result


class TestSearchKnowledgeTool:
    @pytest.mark.asyncio
    async def test_search_finds_metadata(self, loaded_session, kb):
        session, _, _ = loaded_session
        kb.upsert_table("sample", description="Тестовые данные клиентов")
        handler = get_tool_handler("search_knowledge")
        result = await handler(session, query="клиентов")
        assert "Метаданные" in result
        assert "sample" in result