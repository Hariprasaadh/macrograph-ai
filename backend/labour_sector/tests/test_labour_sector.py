"""Pytest test suite for the Labour Sector."""
from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest
import httpx

from labour_sector.models import (
    Citation,
    DataFreshness,
    LabourForceParticipationRecord,
    UnemploymentRecord,
    UnavailableResponse,
    WorkerPopulationRatioRecord,
)
from labour_sector import client as labour_client
from labour_sector.parsers import parse_unemployment_records


@pytest.fixture
def valid_citation() -> Citation:
    return Citation(
        source_authority="Ministry of Statistics and Programme Implementation (MoSPI)",
        document_title="Periodic Labour Force Survey (PLFS)",
        table_reference="labour_sector.plfs_unemployment",
        retrieval_url="https://mcp.mospi.gov.in/",
        observation_period="2024-Q1",
        freshness=DataFreshness.LIVE,
    )


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_labour.duckdb"
    monkeypatch.setattr("labour_sector.database._DB_PATH", db_path)
    from labour_sector import database
    database._DB_PATH = db_path
    database.initialise_schema(seed_baseline=False)
    yield db_path


class TestLabourModels:
    def test_unemployment_record(self, valid_citation):
        rec = UnemploymentRecord(
            period="2024-Q1",
            unemployment_rate_pct=3.2,
            unemployment_rate_urban_pct=6.7,
            unemployment_rate_rural_pct=2.4,
            citation=valid_citation,
        )
        assert rec.unemployment_rate_pct == 3.2

    def test_sector_ownership_boundary(self, valid_citation):
        """Labour cannot own CPI (Prices sector owns CPI)."""
        rec = UnemploymentRecord(
            period="2024-Q1",
            unemployment_rate_pct=3.2,
            citation=valid_citation,
        )
        assert not hasattr(rec, "headline_cpi")


class TestLabourDatabase:
    def test_upsert_and_query_unemployment(self, temp_db, valid_citation):
        from labour_sector import database
        row = {
            "period": "2024-Q1",
            "unemployment_rate_pct": 3.2,
            "unemployment_rate_urban_pct": 6.7,
            "unemployment_rate_rural_pct": 2.4,
            "unemployment_rate_youth_pct": 10.0,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("unemployment", [row])
        assert written == 1

        rows = database.query_latest_rows("unemployment", 10)
        assert len(rows) == 1
        assert rows[0]["unemployment_rate_pct"] == 3.2


class TestLabourAPI:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from labour_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json()["sector"] == "labour_sector"


class TestLivePLFSIntegration:
    def test_monthly_mospi_record_period_and_aggregate_are_parsed(self):
        records = parse_unemployment_records({
            "data": [{
                "Year": 2026,
                "Month": 8,
                "AgeGroup": "15 years and above",
                "Gender": "Person",
                "Sector": "Rural + Urban",
                "Indicator": "Unemployment Rate",
                "Value": "5.4",
            }]
        })

        assert records == [{
            "period": "2026-08",
            "unemployment_rate_pct": 5.4,
            "unemployment_rate_urban_pct": None,
            "unemployment_rate_rural_pct": None,
            "unemployment_rate_youth_pct": None,
            "citation": "https://mcp.mospi.gov.in/",
        }]

    @pytest.mark.asyncio
    async def test_live_workflow_resolves_indicator_and_metadata_filters(self, monkeypatch):
        calls = []

        async def call_tool(_client, request_id, name, arguments):
            calls.append((request_id, name, arguments))
            if name == "list_datasets":
                return {"datasets": [{"dataset": "PLFS"}]}
            if name == "get_indicators":
                return {
                    "indicators": [
                        {"indicator_code": 1, "indicator_name": "Labour Force Participation Rate"},
                        {"indicator_code": 2, "indicator_name": "Worker Population Ratio"},
                        {"indicator_code": 3, "indicator_name": "Unemployment Rate"},
                    ]
                }
            if name == "get_metadata":
                return {
                    "filter_values": {
                        "data": {
                            "gender": [{"code": 3, "label": "Person"}],
                            "age": [{"code": 1, "label": "15 years and above"}],
                            "sector": [{"code": 3, "label": "Rural + Urban"}],
                        }
                    }
                }
            return {"data": [{"year": 2026, "month": 8, "value": 5.4}]}

        monkeypatch.setattr(labour_client, "_call_mcp_tool", call_tool)

        data, indicator_code, indicator_name = await labour_client._fetch_plfs_indicator(
            "unemployment"
        )

        assert indicator_code == 3
        assert "unemployment rate" in indicator_name
        assert [name for _, name, _ in calls] == [
            "list_datasets", "get_indicators", "get_metadata", "get_data"
        ]
        get_data_filters = calls[-1][2]["filters"]
        assert get_data_filters == {
            "indicator_code": 3,
            "frequency_code": 3,
            "gender_code": 3,
            "age_code": 1,
            "sector_code": 3,
        }
        assert data["data"][0]["month"] == 8

    @pytest.mark.asyncio
    async def test_agent_preserves_dictionary_values_and_citations(self, monkeypatch):
        citation = {
            "source_agent": "labour_sector",
            "source_authority": "MoSPI",
            "table_reference": "PLFS indicator 3",
            "retrieval_url": "https://mcp.mospi.gov.in/",
            "observation_period": "2026-08",
            "freshness": "live",
        }

        async def unemployment():
            return [{"period": "2026-08", "unemployment_rate_pct": 5.4, "citation": citation}]

        async def lfpr():
            return [{"period": "2026-08", "lfpr_total_pct": 55.2, "citation": citation}]

        async def wpr():
            return [{"period": "2026-08", "wpr_total_pct": 52.1, "citation": citation}]

        monkeypatch.setattr(labour_client, "fetch_unemployment_snapshot", unemployment)
        monkeypatch.setattr(labour_client, "fetch_labour_force_participation", lfpr)
        monkeypatch.setattr(labour_client, "fetch_worker_population_ratio", wpr)

        from labour_sector import agent as labour_agent

        async def select_indicators(**_kwargs):
            return {"unemployment", "lfpr", "wpr"}, None

        async def summarize_evidence(**_kwargs):
            return "The returned labour records contain the latest reported rates."

        monkeypatch.setattr(
            labour_agent, "select_relevant_services_with_llm", select_indicators
        )
        monkeypatch.setattr(labour_agent, "reason_over_sector_data", summarize_evidence)

        labour_agent_node = labour_agent.labour_agent_node
        result = await labour_agent_node({"query": "Latest rates?"})

        assert result["labour_sector_data"]["unemployment"] == {
            "period": "2026-08",
            "unemployment_rate_pct": 5.4,
        }
        assert result["labour_sector_freshness"]["unemployment"] == "live"
        assert len(result["labour_sector_citations"]) == 3
        assert "None%" not in result["labour_sector_analysis"]
