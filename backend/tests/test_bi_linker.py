from __future__ import annotations

import pytest

from app.services.bi_linker import (
    build_bi_link,
    build_superset_url,
    build_grafana_url,
    build_datalens_url,
)


class TestSupersetUrl:
    def test_basic_url(self):
        url = build_superset_url("https://superset.company.com", "5")
        assert "superset.company.com/superset/dashboard/5/" in url

    def test_with_params(self):
        url = build_superset_url("https://s.com", "5", {"region": "Москва"})
        assert "fltr_col=region" in url
        assert "fltr_val=" in url
        assert "fltr_op=in" in url

    def test_strips_trailing_slash(self):
        url = build_superset_url("https://s.com/", "5")
        assert "s.com/superset/dashboard/5/" in url

    def test_no_params(self):
        url = build_superset_url("https://s.com", "5")
        assert "?" not in url


class TestGrafanaUrl:
    def test_basic_url(self):
        url = build_grafana_url("https://grafana.com", "abc123")
        assert "grafana.com/d/abc123" in url

    def test_with_vars(self):
        url = build_grafana_url("https://g.com", "abc", {"host": "server1"})
        assert "var-host=server1" in url

    def test_with_time_range(self):
        url = build_grafana_url("https://g.com", "abc", None, ("2024-01-01", "2024-02-01"))
        assert "from=2024-01-01" in url
        assert "to=2024-02-01" in url

    def test_no_params(self):
        url = build_grafana_url("https://g.com", "abc")
        assert "?" not in url


class TestDatalensUrl:
    def test_basic_url(self):
        url = build_datalens_url("https://datalens.com", "chart1")
        assert "datalens.com/chart1" in url

    def test_with_params(self):
        url = build_datalens_url("https://dl.com", "chart1", {"region": "MSK"})
        assert "region=MSK" in url


class TestBuildBiLinkDispatcher:
    def test_superset(self):
        url = build_bi_link("superset", "https://s.com", "5", {"region": "x"})
        assert "superset/dashboard/5" in url

    def test_grafana(self):
        url = build_bi_link("grafana", "https://g.com", "abc")
        assert "/d/abc" in url

    def test_datalens(self):
        url = build_bi_link("datalens", "https://dl.com", "chart1")
        assert "dl.com/chart1" in url

    def test_tableau(self):
        url = build_bi_link("tableau", "https://tab.com", "workbook/sheet", {"filter": "val"})
        assert "tab.com/views/workbook/sheet" in url
        assert ":embed=yes" in url

    def test_powerbi(self):
        url = build_bi_link("powerbi", "https://pbi.com", "rep123", {"region": "Москва"})
        assert "reportEmbed" in url
        assert "rep123" in url
        assert "Table/region eq 'Москва'" in url

    def test_unknown_tool_fallback(self):
        url = build_bi_link("unknown", "https://x.com", "5")
        assert "x.com/5" in url

    def test_empty_params(self):
        url = build_bi_link("superset", "https://s.com", "5", None)
        assert "?" not in url

    def test_strips_base_url_slash(self):
        url = build_bi_link("superset", "https://s.com//", "5")
        assert "s.com/superset/dashboard/5" in url