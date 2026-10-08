"""Unit tests for the Real Sector & Industrial Output module."""
from __future__ import annotations

import asyncio
import pytest
from real_sector import client
from real_sector import database as db
from real_sector.executor import RealSectorAgentExecutor
from real_sector.mcp_server import (
    get_core_industries,
    get_iip_sectoral,
    get_iip_use_based,
    get_infrastructure_market_context,
    get_joined_real_sector_indicators,
    get_manufacturing_gva,
)
from real_sector.models import DataFreshness
from real_sector.parsers import evaluate_industrial_trends


@pytest.fixture(autouse=True)
def setup_test_db():
    db.initialise_schema(seed_baseline=True)


def test_iip_sectoral_fetch():
    records = asyncio.run(client.fetch_iip_sectoral(lookback_months=6))
    assert len(records) > 0
    assert records[0].citation is not None
    assert records[0].period is not None


def test_iip_use_based_fetch():
    records = asyncio.run(client.fetch_iip_use_based(lookback_months=6))
    assert len(records) > 0
    assert records[0].citation.source_authority == "Ministry of Statistics and Programme Implementation (MoSPI)"


def test_core_industries_fetch():
    records = asyncio.run(client.fetch_core_industries(lookback_months=6))
    assert len(records) > 0
    assert records[0].overall_ici_yoy_pct is not None


def test_duckdb_joined_query_and_trends():
    records = asyncio.run(client.fetch_joined_real_indicators())
    assert len(records) > 0
    latest = records[0]
    assert latest.period is not None
    assert latest.trend_summary is not None


def test_trend_evaluator():
    trends = evaluate_industrial_trends(
        manufacturing_yoy=-0.5,
        capital_goods_yoy=0.5,
        steel_yoy=4.2,
        cement_yoy=3.1,
    )
    assert "\u2193" in trends["Manufacturing IIP"]
    assert "\u2191" in trends["Capital Goods IIP"]
    assert "\u2191" in trends["Core Steel"]
    assert "\u2191" in trends["Core Cement"]


def test_mcp_tools():
    res_iip = asyncio.run(get_iip_sectoral(lookback_months=3))
    if hasattr(res_iip, "records"):
        assert res_iip.status in (DataFreshness.LIVE, DataFreshness.CACHED)
        assert len(res_iip.records) > 0
    else:
        assert res_iip.status == DataFreshness.UNAVAILABLE

    res_ici = asyncio.run(get_core_industries(lookback_months=3))
    if hasattr(res_ici, "records"):
        assert len(res_ici.records) > 0
    else:
        assert res_ici.status == DataFreshness.UNAVAILABLE

    res_gva = asyncio.run(get_manufacturing_gva(lookback_quarters=2))
    if hasattr(res_gva, "records"):
        assert len(res_gva.records) > 0
    else:
        assert res_gva.status == DataFreshness.UNAVAILABLE

    res_joined = asyncio.run(get_joined_real_sector_indicators())
    if hasattr(res_joined, "records"):
        assert len(res_joined.records) > 0
    else:
        assert res_joined.status == DataFreshness.UNAVAILABLE

    res_mkt = asyncio.run(get_infrastructure_market_context())
    if hasattr(res_mkt, "records"):
        assert len(res_mkt.records) > 0
    else:
        assert res_mkt.status == DataFreshness.UNAVAILABLE


def test_a2a_agent_card():
    card = RealSectorAgentExecutor.get_agent_card()
    assert card.name == "Real Sector & Industrial Output Specialist Agent"
    assert len(card.skills) >= 4
    skill_ids = [s.id for s in card.skills]
    assert "iip_industrial_analysis" in skill_ids
    assert "core_industries_analysis" in skill_ids
