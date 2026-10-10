"""Unit tests for Real Sector GDP/GFCF (MoSPI NAS) and growth enrichment.

All MoSPI/IMF/Yahoo/Tavily network calls are mocked — no live dependency.
"""
from __future__ import annotations

import asyncio

import pytest

from real_sector import national_accounts as na
from real_sector.agent import _select_services_deterministically
from real_sector.market_client import _parse_ddg_html, fetch_free_web_search
from real_sector.mcp_server import get_gdp, get_gfcf
from real_sector.models import DataFreshness


def _gdp_row(year, current, constant, revision="Provisional Estimates"):
    return {
        "base_year": "2011-12", "series": "Current", "year": year,
        "indicator": "Gross Domestic Product", "frequency": "Annual",
        "revision": revision, "quarter": None,
        "current_price": str(current), "constant_price": str(constant),
        "unit": "Rs Crore",
    }


def _gfcf_row(year, current, constant, revision="Provisional Estimates"):
    row = _gdp_row(year, current, constant, revision)
    row["indicator"] = "Gross Fixed Capital Formation"
    row["institutional_sector"] = None
    return row


GDP_ROWS = [
    _gdp_row("2022-23", 26949646, 16000000, "Final Estimates"),
    _gdp_row("2023-24", 29535666, 17381721, "Provisional Estimates"),
    _gdp_row("2023-24", 29389685, 17290281, "Second Advance Estimates"),
    _gdp_row("2024-25", 33068145, 18796955, "Provisional Estimates"),
]

GFCF_ROWS = [
    _gfcf_row("2022-23", 8000000, 5400000, "Final Estimates"),
    _gfcf_row("2023-24", 8832160, 5994586, "Provisional Estimates"),
    _gfcf_row("2024-25", 9886129, 6333084, "Provisional Estimates"),
]


def _mock_nas_factory():
    async def _mock(tool_name, arguments):
        code = arguments["filters"]["indicator_code"]
        rows = GDP_ROWS if code == 5 else GFCF_ROWS
        return {"data": rows, "meta_data": {"page": 1, "totalPages": 1}}
    return _mock


def test_fetch_gdp_real_nominal_and_yoy(monkeypatch):
    monkeypatch.setattr(na, "_call_nas_mcp", _mock_nas_factory())
    records = asyncio.run(na.fetch_gdp(lookback_years=3))
    assert len(records) == 3
    latest = records[-1]
    assert latest.period == "2024-25"
    assert latest.nominal_gdp_cr == 33068145.0
    assert latest.real_gdp_cr == 18796955.0
    # 2024-25 vs 2023-24 provisional vintage
    assert latest.real_gdp_yoy_pct == pytest.approx((18796955 - 17381721) / 17381721 * 100, rel=1e-3)
    assert latest.nominal_gdp_yoy_pct == pytest.approx((33068145 - 29535666) / 29535666 * 100, rel=1e-3)
    assert latest.gdp_deflator_yoy_pct is not None
    assert latest.base_year == "2011-12"
    assert latest.citation.source_agent == "real_sector"
    assert "NAS" in latest.citation.table_reference or "indicator_code=5" in latest.citation.table_reference


def test_fetch_gdp_prefers_latest_vintage(monkeypatch):
    monkeypatch.setattr(na, "_call_nas_mcp", _mock_nas_factory())
    records = asyncio.run(na.fetch_gdp(lookback_years=3))
    rec_2324 = next(r for r in records if r.period == "2023-24")
    assert rec_2324.revision == "Provisional Estimates"
    assert rec_2324.nominal_gdp_cr == 29535666.0


def test_fetch_gfcf_and_investment_rate(monkeypatch):
    monkeypatch.setattr(na, "_call_nas_mcp", _mock_nas_factory())
    records = asyncio.run(na.fetch_gfcf(lookback_years=3))
    assert len(records) == 3
    latest = records[-1]
    assert latest.period == "2024-25"
    assert latest.real_gfcf_cr == 6333084.0
    assert latest.nominal_gfcf_cr == 9886129.0
    assert latest.gfcf_to_gdp_pct == pytest.approx(9886129 / 33068145 * 100, rel=1e-3)
    assert latest.real_gfcf_yoy_pct == pytest.approx((6333084 - 5994586) / 5994586 * 100, rel=1e-3)


def test_fetch_gdp_empty_raises_unavailable(monkeypatch):
    async def _empty(tool_name, arguments):
        return {"data": [], "meta_data": {"page": 1, "totalPages": 1}}
    monkeypatch.setattr(na, "_call_nas_mcp", _empty)
    with pytest.raises(na.RealSectorDataUnavailableError):
        asyncio.run(na.fetch_gdp(lookback_years=3))


def test_mcp_tools_gdp_gfcf(monkeypatch):
    monkeypatch.setattr(na, "_call_nas_mcp", _mock_nas_factory())
    res_gdp = asyncio.run(get_gdp(lookback_years=3))
    assert res_gdp.status == DataFreshness.LIVE
    assert len(res_gdp.records) == 3
    res_gfcf = asyncio.run(get_gfcf(lookback_years=3))
    assert res_gfcf.status == DataFreshness.LIVE
    assert len(res_gfcf.records) == 3


def test_mcp_tool_unavailable_sentinel(monkeypatch):
    async def _boom(tool_name, arguments):
        raise RuntimeError("offline")

    async def _boom_imf(lookback_years):
        raise na.RealSectorDataUnavailableError("offline")

    monkeypatch.setattr(na, "_call_nas_mcp", _boom)
    monkeypatch.setattr(na, "_fetch_gdp_imf_fallback", _boom_imf)
    res = asyncio.run(get_gdp(lookback_years=3))
    assert res.status == DataFreshness.UNAVAILABLE
    assert "gdp" in res.tool


def test_service_selection_gdp_gfcf():
    assert "gdp" in _select_services_deterministically("What is India's latest real GDP growth?")
    assert "gfcf" in _select_services_deterministically("How is gross fixed capital formation trending?")
    assert "gdp" in _select_services_deterministically("nominal GDP and deflator overview")
    full = _select_services_deterministically("comprehensive real sector diagnostic")
    assert {"gdp", "gfcf", "iip_sectoral", "market_context"} <= full


def test_ddg_html_parser():
    page = (
        '<a class="result__a" href="https://example.com/gdp">India GDP grows 7%</a>'
        '<a class="result__snippet" href="x">MoSPI reports <b>7.4%</b> growth &amp; outlook</a>'
    )
    hits = _parse_ddg_html(page, 5)
    assert len(hits) == 1
    assert hits[0]["url"] == "https://example.com/gdp"
    assert "7.4%" in hits[0]["snippet"]
    assert "<b>" not in hits[0]["snippet"]


def test_free_search_failure_degrades(monkeypatch):
    import httpx

    class _Boom:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            raise RuntimeError("offline")

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(httpx, "AsyncClient", _Boom)
    res = asyncio.run(fetch_free_web_search("India GDP"))
    assert res["status"] == "unavailable"
    assert res["hits"] == []
