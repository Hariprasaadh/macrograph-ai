"""Regression tests for nullable dashboard telemetry, without live services."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import dashboard


@pytest.fixture
def telemetry():
    return [
        {"credit_growth": {"non_food_credit_yoy_pct": 13.0},
         "asset_quality": {"gross_npa_pct": 2.8, "provision_coverage_ratio_pct": 76.4}},
        {},
        {"latest_fx": {"usd_inr_rate": 85.57},
         "latest_reserves": {"total_reserves_usd_mn": 700000}},
        {"latest_gsec": {"ten_year_gsec_yield_pct": 6.77}},
    ]


@pytest.mark.parametrize("sector,record,field", [
    (0, "credit_growth", "non_food_credit_yoy_pct"),
    (0, "asset_quality", "gross_npa_pct"),
    (0, "asset_quality", "provision_coverage_ratio_pct"),
    (2, "latest_fx", "usd_inr_rate"),
    (2, "latest_reserves", "total_reserves_usd_mn"),
    (3, "latest_gsec", "ten_year_gsec_yield_pct"),
])
@pytest.mark.parametrize("missing", ["record", "null", "key"])
def test_brief_missing_data(telemetry, sector, record, field, missing):
    if missing == "record":
        telemetry[sector][record] = None
    elif missing == "null":
        telemetry[sector][record][field] = None
    else:
        del telemetry[sector][record][field]
    brief = dashboard._generate_macro_intelligence_brief(*telemetry)
    assert brief["status"] == "unavailable"
    assert f"{record}.{field}" in brief["missing_metrics"]
    assert brief["key_drivers"] == []


@pytest.mark.parametrize("yield_value", [6.77, 0.0])
def test_brief_preserves_numeric_yields(telemetry, yield_value):
    telemetry[3]["latest_gsec"]["ten_year_gsec_yield_pct"] = yield_value
    brief = dashboard._generate_macro_intelligence_brief(*telemetry)
    assert f"{yield_value:.2f}%" in brief["key_drivers"][3]["takeaway"]


def test_anomaly_missing_provision_coverage():
    anomalies = dashboard._compute_macro_anomalies(
        {"asset_quality": {"gross_npa_pct": 2.8, "provision_coverage_ratio_pct": None}}, {}, {}
    )
    assert "Provision coverage ratio is unavailable" in anomalies[0]["description"]


@pytest.mark.parametrize("gsec", [None, {}, {"period": "test", "ten_year_gsec_yield_pct": None},
                                 {"ten_year_gsec_yield_pct": 0.0}])
def test_overview_returns_200_for_missing_gsec(monkeypatch, gsec):
    for sector in ("finance", "fiscal", "external", "labour", "monetary", "real", "services"):
        monkeypatch.setattr(dashboard, f"query_{sector}_telemetry", lambda: {})
    monkeypatch.setattr(dashboard, "query_capmarkets_telemetry", lambda: {"latest_gsec": gsec})

    async def empty_open_data():
        return {}

    for name in ("union_budget", "state_finances", "employment_open", "economy_survey", "rbi_dbie_live"):
        monkeypatch.setattr(dashboard, f"get_{name}_telemetry", empty_open_data)
    app = FastAPI()
    app.include_router(dashboard.router)
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    assert response.json()["daily_brief"]["status"] == "unavailable"
    card = next(item for item in response.json()["other_sectors_preview"]
                if item["indicator"] == "10-Year Benchmark G-Sec Yield")
    if gsec and gsec.get("ten_year_gsec_yield_pct") == 0.0:
        assert card["value"] == "0.00%"
    else:
        assert card["value"] == "Unavailable"
        assert card["status"] == "unavailable"


@pytest.mark.parametrize("value", [float('nan'), float('inf'), True, 'not available'])
def test_brief_rejects_invalid_yield(telemetry, value):
    telemetry[3]["latest_gsec"]["ten_year_gsec_yield_pct"] = value
    brief = dashboard._generate_macro_intelligence_brief(*telemetry)
    assert brief["status"] == "unavailable"
    assert "latest_gsec.ten_year_gsec_yield_pct" in brief["missing_metrics"]
