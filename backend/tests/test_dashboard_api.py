"""Tests for the dashboard overview and telemetry endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(main.app)


def test_dashboard_overview_status_and_keys(client: TestClient) -> None:
    """Verifies /api/v1/dashboard/overview returns 200 with required top-level keys."""
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    payload = response.json()

    assert payload.get("status") == "success"
    assert "finance_sector" in payload
    assert "fiscal_sector" in payload
    assert "real_sector" in payload
    assert "services_sector" in payload
    assert "timeseries" in payload
    assert "other_sectors_preview" in payload
    assert "platform_summary" in payload


def test_dashboard_finance_indicators_and_citations(client: TestClient) -> None:
    """Verifies Finance sector data contains authentic metrics and anti-hallucination citations."""
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    finance = response.json().get("finance_sector", {})

    # 1. Credit growth
    credit = finance.get("credit_growth")
    if credit:
        assert "non_food_credit_cr" in credit
        assert "non_food_credit_yoy_pct" in credit
        assert "citation" in credit
        assert credit["citation"].get("source_agent") == "finance_sector"
        assert credit["citation"].get("table_reference") is not None

    # 2. Asset quality
    asset = finance.get("asset_quality")
    if asset:
        assert "gross_npa_pct" in asset
        assert "crar_pct" in asset
        assert "citation" in asset
        assert asset["citation"].get("source_agent") == "finance_sector"


def test_dashboard_timeseries_arrays(client: TestClient) -> None:
    """Verifies that historical time series are populated for charting."""
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    timeseries = response.json().get("timeseries", {})

    assert "credit" in timeseries
    assert "asset_quality" in timeseries
    assert "lending_rates" in timeseries
    assert "deposits" in timeseries

    # If seeded, credit should have history
    assert len(timeseries["credit"]) > 0
    first_pt = timeseries["credit"][0]
    assert "period" in first_pt
    assert "non_food_credit_cr" in first_pt


def test_dashboard_multi_sector_telemetry(client: TestClient) -> None:
    """Verifies active multi-sector integration across fiscal, real, and services sectors."""
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    payload = response.json()

    # Fiscal sector
    fiscal = payload.get("fiscal_sector", {})
    assert "gst_history" in fiscal
    assert "deficit_history" in fiscal
    assert len(fiscal["gst_history"]) > 0

    # Platform summary active live sectors
    summary = payload.get("platform_summary", {})
    active_sectors = summary.get("active_live_sectors", [])
    assert "finance_sector" in active_sectors
    assert "fiscal_sector" in active_sectors


def test_dashboard_open_data_telemetry(client: TestClient) -> None:
    """Verifies Indian Data Project open datasets (Budget, States, Employment, Economy)."""
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    payload = response.json()

    assert "union_budget" in payload
    budget = payload["union_budget"]
    assert "summary" in budget
    assert "totalExpenditure" in budget["summary"]
    assert "ministries" in budget
    assert len(budget["ministries"]) > 0

    assert "state_finances" in payload
    states = payload["state_finances"]
    assert "summary" in states
    assert "states" in states
    assert len(states["states"]) > 0

    assert "employment_open" in payload
    assert "economy_survey" in payload

    assert "rbi_dbie_live" in payload
    dbie = payload["rbi_dbie_live"]
    assert "m3_series" in dbie
    assert len(dbie["m3_series"]) > 0
    assert "tables_catalog" in dbie
    assert len(dbie["tables_catalog"]) > 0
    assert "citation" in dbie


