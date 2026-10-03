"""Pytest test suite for the Monetary Sector."""
from __future__ import annotations

import json
from datetime import datetime, timezone
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from monetary_sector.models import (
    Citation,
    DataFreshness,
    MoneySupplyRecord,
    MonetaryStanceRecord,
    PolicyRatesRecord,
    SystemLiquidityRecord,
    UnavailableResponse,
)
from monetary_sector.parsers import parse_money_supply, parse_policy_rates, parse_system_liquidity


@pytest.fixture
def valid_citation() -> Citation:
    return Citation(
        source_authority="Reserve Bank of India (RBI)",
        document_title="Select Economic Indicators (Monthly), RBI Bulletin Table 1",
        table_reference="/banking/select-economic-indicators",
        retrieval_url="https://dbie.rbihub.in/banking/select-economic-indicators",
        observation_period="test-period",
        freshness=DataFreshness.UPSTREAM_SNAPSHOT,
        source_base_url="https://dbie.rbihub.in",
        source_note="Data reflects the deployment's last scrape.",
        frequency="Monthly",
    )


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_monetary.duckdb"
    monkeypatch.setattr("monetary_sector.database._DB_PATH", db_path)
    from monetary_sector import database
    database._DB_PATH = db_path
    database.initialise_schema(seed_baseline=False)
    yield db_path


class TestMonetaryModels:
    def test_policy_rates_record(self, valid_citation):
        rec = PolicyRatesRecord(
            period="test-period",
            repo_rate_pct=6.50,
            sdf_rate_pct=6.25,
            msf_rate_pct=6.75,
            crr_pct=4.50,
            slr_pct=18.00,
            citation=valid_citation,
        )
        assert rec.repo_rate_pct == 6.50
        assert rec.citation.freshness == DataFreshness.UPSTREAM_SNAPSHOT

    def test_unavailable_response(self):
        resp = UnavailableResponse(tool="get_policy_rates", reason="DBIE API unavailable")
        assert resp.status == DataFreshness.UNAVAILABLE


class TestMonetaryDatabase:
    def test_schema_and_upsert(self, temp_db, valid_citation):
        from monetary_sector import database
        row = {
            "period": "test-period",
            "repo_rate_pct": 6.50,
            "reverse_repo_rate_pct": 3.35,
            "sdf_rate_pct": 6.25,
            "msf_rate_pct": 6.75,
            "bank_rate_pct": 6.75,
            "crr_pct": 4.50,
            "slr_pct": 18.00,
            "citation": valid_citation.model_dump_json(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        written = database.upsert_rows("policy_rates", [row])
        assert written == 1

        rows = database.query_latest_rows("policy_rates", 10)
        assert len(rows) == 1
        assert rows[0]["repo_rate_pct"] == 6.50


class TestDBIEMCPParsers:
    source = {
        "document_title": "Select Economic Indicators (Monthly), RBI Bulletin Table 1",
        "table_reference": "/banking/select-economic-indicators",
        "retrieval_url": "https://dbie.rbihub.in/banking/select-economic-indicators",
        "source_base_url": "https://dbie.rbihub.in",
        "source_note": "Data reflects the deployment's last scrape.",
        "frequency": "Monthly",
    }

    def test_policy_rates_payload_shape(self):
        records = parse_policy_rates(
            {
                "data": [{
                    "month": "test-period",
                    "policy_repo_rate": 5.25,
                    "reverse_repo_rate": 3.35,
                    "sdf_rate": 5,
                    "msf_rate": 5.5,
                    "bank_rate": 5.5,
                    "crr": 3,
                    "slr": 18,
                }],
            },
            source=self.source,
        )
        assert records[0].repo_rate_pct == 5.25
        assert records[0].citation.table_reference == "/banking/select-economic-indicators"
        assert records[0].citation.freshness == DataFreshness.UPSTREAM_SNAPSHOT
        assert "last scrape" in records[0].citation.source_note

    def test_money_stock_payload_shape(self):
        records = parse_money_supply(
            {
                "units": "Rupees crores",
                "data": [{
                    "date": "test-period",
                    "values": {
                        "currencyWithThePublic": 4210170,
                        "demandDepositsWithBanks": 3491475,
                        "otherDepositsWithReserveBank": 123368,
                        "m1": None,
                        "postOfficeSavingsDeposits": None,
                        "m2": None,
                        "timeDepositsWithBanks": 25242433,
                        "m3": 33067446,
                        "m3_excl": None,
                    },
                }],
            },
            source={
                **self.source,
                "document_title": "Money Stock Measures, RBI Bulletin Table 6",
                "table_reference": "/banking/money-stock-measures",
                "retrieval_url": "https://dbie.rbihub.in/banking/money-stock-measures",
                "frequency": "Fortnightly",
            },
        )
        assert records[0].period == "test-period"
        assert records[0].m3_cr == 33067446
        assert records[0].m1_cr is None
        assert records[0].m3_yoy_pct is None
        assert records[0].citation.unit == "Rupees crores"

    def test_liquidity_does_not_infer_net_laf(self):
        records = parse_system_liquidity(
            {
                "unit": "Rupees Crores",
                "data": [{
                    "date": "Sep 20, 2026",
                    "repo": None,
                    "reverse_repo": None,
                    "variable_rate_repo": None,
                    "variable_rate_reverse_repo": None,
                    "msf": 82,
                    "sdf": 91747,
                    "standing_liquidity_facilities": None,
                    "omo_sale": None,
                    "omo_purchase": None,
                }],
            },
            source={
                **self.source,
                "document_title": "Liquidity Operations by RBI, RBI Bulletin Table 3",
                "table_reference": "/banking/liquidity-operations",
                "retrieval_url": "https://dbie.rbihub.in/banking/liquidity-operations",
                "frequency": "Daily",
            },
        )
        assert records[0].msf_operations_cr == 82
        assert records[0].net_laf_absorption_cr is None
        assert records[0].liquidity_condition is None
        assert records[0].citation.source_values["sdf"] == 91747

    def test_cache_preserves_newest_first_order(self, temp_db, valid_citation):
        from monetary_sector.client import _load_cache, _save_records

        newer = PolicyRatesRecord(
            period="newer-test-period",
            repo_rate_pct=2,
            citation=valid_citation.model_copy(
                update={"observation_period": "newer-test-period"}
            ),
        )
        older = PolicyRatesRecord(
            period="older-test-period",
            repo_rate_pct=1,
            citation=valid_citation.model_copy(
                update={"observation_period": "older-test-period"}
            ),
        )
        _save_records("policy_rates", [newer, older], "test_policy_rates")
        records = _load_cache("policy_rates", 2, PolicyRatesRecord, "test_policy_rates")
        assert [record.period for record in records] == [
            "newer-test-period",
            "older-test-period",
        ]


class TestMonetaryAPI:
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from httpx import AsyncClient, ASGITransport
        from monetary_sector.api.app import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json()["sector"] == "monetary_sector"
