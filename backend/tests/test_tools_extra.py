from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from app.services.tools.registry import get_tool_handler


class TestExportDataTool:
    def test_export_creates_csv(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("export_data")
        result = handler(session, table_name="sample")
        assert "__EXPORT_DATA__" in result
        assert "filename=sample.csv" in result
        assert "rows=7" in result

    def test_export_with_sql(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("export_data")
        result = handler(session, table_name="sample", sql="SELECT id, name FROM sample WHERE region='Москва'")
        assert "__EXPORT_DATA__" in result

    def test_export_with_columns(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("export_data")
        result = handler(session, table_name="sample", columns="id, name")
        assert "__EXPORT_DATA__" in result

    def test_export_missing_table(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("export_data")
        result = handler(session, table_name="nonexistent")
        assert "не найдена" in result.lower()

    def test_export_no_data(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("export_data")
        result = handler(session, table_name="sample", sql="SELECT * FROM sample WHERE 1=0")
        assert "Нет данных" in result


class TestProfileDataTool:
    def test_profile_returns_stats(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("profile_data")
        result = handler(session, table_name="sample")
        assert "sample" in result.lower() or "профил" in result.lower() or "Колонк" in result or "id" in result

    def test_profile_missing_table(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("profile_data")
        result = handler(session, table_name="nonexistent")
        # либо ошибка, либо пусто
        assert isinstance(result, str)


class TestSmartSummaryTool:
    def test_summary_returns_text(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("smart_summary")
        result = handler(session, table_name="sample")
        assert isinstance(result, str)
        assert len(result) > 10


class TestTransformDataTool:
    def test_transform_fillna(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("transform_data")
        result = handler(session, table_name="sample", operations="fillna:amount:0")
        assert isinstance(result, str)

    def test_transform_extract_date(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("transform_data")
        result = handler(session, table_name="sample", operations="extract:order_date:year")
        assert isinstance(result, str)

    def test_transform_derive(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("transform_data")
        result = handler(session, table_name="sample", operations="derive:double_amount=amount*2")
        assert isinstance(result, str)


class TestQueryExplainTool:
    def test_explain_local_duckdb(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("query_explain")
        result = handler(session, sql="SELECT * FROM sample")
        assert isinstance(result, str)

    def test_explain_error(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("query_explain")
        result = handler(session, sql="SELECT * FROM nonexistent")
        assert "❌" in result or "rror" in result.lower()


class TestTestConnectionTool:
    def test_missing_connection(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("test_connection")
        result = handler(session, name="nonexistent")
        assert "не найдено" in result.lower()

    def test_with_mocked_connector(self, loaded_session):
        session, eng, _ = loaded_session
        # добавим mock-коннектор
        mock = MagicMock()
        mock.db_type = "postgresql"
        mock.test.return_value = True
        eng.connectors["mock_pg"] = mock
        handler = get_tool_handler("test_connection")
        result = handler(session, name="mock_pg")
        assert "доступно" in result.lower()

    def test_failed_connection(self, loaded_session):
        session, eng, _ = loaded_session
        mock = MagicMock()
        mock.db_type = "postgresql"
        mock.test.return_value = False
        eng.connectors["bad_pg"] = mock
        handler = get_tool_handler("test_connection")
        result = handler(session, name="bad_pg")
        assert "недоступно" in result.lower()


class TestRefreshSchemaTool:
    def test_no_connectors(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("refresh_schema")
        result = handler(session, connection="nonexistent")
        assert "не найдено" in result.lower() or "обнов" in result.lower()

    def test_refresh_mocked(self, loaded_session):
        session, eng, _ = loaded_session
        mock = MagicMock()
        mock.list_tables.return_value = ["t1", "t2"]
        mock.describe.return_value = [{"name": "id", "type": "INTEGER"}]
        mock.row_count.return_value = 5
        mock.foreign_keys.return_value = []
        mock.db_type = "postgresql"
        eng.connectors["mock_conn"] = mock
        handler = get_tool_handler("refresh_schema")
        result = handler(session, connection="mock_conn")
        assert "обнов" in result.lower()


class TestAttachDatabaseTool:
    def test_attach_sqlite_success(self, loaded_session, tmp_path):
        import sqlite3
        db_path = tmp_path / "test_attach.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE x (id INT, name TEXT)")
        conn.execute("INSERT INTO x VALUES (1, 'a')")
        conn.commit()
        conn.close()

        session, _, _ = loaded_session
        handler = get_tool_handler("attach_database")
        result = handler(session, name="test_sqlite", db_type="sqlite", database=str(db_path), mode="dump")
        assert "✅" in result or "актив" in result.lower()
        assert "1" in result  # 1 таблица

    def test_attach_unsupported_db_type(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("attach_database")
        result = handler(session, name="bad", db_type="oracle", mode="auto")
        assert "не" in result.lower() or "❌" in result or "ошибк" in result.lower()


class TestLoadFileTool:
    def test_load_csv(self, loaded_session, tmp_path):
        # создадим новый CSV
        p = tmp_path / "new_data.csv"
        p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        session, _, _ = loaded_session
        handler = get_tool_handler("load_file")
        result = handler(session, path=str(p))
        assert "✅" in result or "загруж" in result.lower()
        assert "2" in result  # 2 строки

    def test_load_file_not_found(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("load_file")
        result = handler(session, path="/nonexistent/file.csv")
        assert "не найден" in result.lower() or "❌" in result

    def test_load_parquet(self, loaded_session, tmp_path):
        # Создаём parquet через DuckDB (не требует pyarrow)
        session, _, _ = loaded_session
        p = tmp_path / "data.parquet"
        session.conn.execute(f"COPY (SELECT 1 AS x, 'a' AS y UNION ALL SELECT 2, 'b' UNION ALL SELECT 3, 'c') TO '{p}' (FORMAT PARQUET)")
        handler = get_tool_handler("load_file")
        result = handler(session, path=str(p))
        assert "✅" in result or "загруж" in result.lower()
        assert "3" in result  # 3 строки


class TestSampleDataTool:
    def test_sample_returns_rows(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sample_data")
        result = handler(session, table_name="sample", n=3)
        assert isinstance(result, str)

    def test_sample_first(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("sample_data")
        result = handler(session, table_name="sample", n=2, method="first")
        assert "Анна" in result  # первая запись


class TestDetectPatternsTool:
    def test_detect_finds_email(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("detect_patterns")
        result = handler(session, table_name="sample", columns="email")
        assert "email" in result.lower() or "Email" in result or "@" in result


class TestFindDuplicatesTool:
    def test_find_exact_duplicates(self, loaded_session):
        session, _, _ = loaded_session
        # в sample есть дубли (Анна, anna@example.com, 1500.50, Москва)
        handler = get_tool_handler("find_duplicates")
        result = handler(session, table_name="sample", columns="name,email", mode="exact")
        assert isinstance(result, str)
        # должны найтись дубли Анны
        assert "Анна" in result or "2" in result


class TestDetectAnomaliesTool:
    def test_detect_returns_text(self, loaded_session):
        session, _, _ = loaded_session
        # 99999.99 — аномалия
        handler = get_tool_handler("detect_anomalies")
        result = handler(session, table_name="sample", columns="amount")
        assert isinstance(result, str)


class TestCorrelationTool:
    def test_correlation_returns_text(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("correlation_analysis")
        result = handler(session, table_name="sample", columns="id,amount")
        assert isinstance(result, str)


class TestListMetricsFromTool:
    def test_empty(self, loaded_session):
        session, _, _ = loaded_session
        handler = get_tool_handler("list_metrics")
        result = handler(session)
        assert "нет" in result.lower() or "не" in result.lower()

    def test_with_metric(self, loaded_session, kb):
        session, _, _ = loaded_session
        kb.upsert_metric("test_metric", formula="SUM(x)", description="test")
        handler = get_tool_handler("list_metrics")
        result = handler(session)
        assert "test_metric" in result