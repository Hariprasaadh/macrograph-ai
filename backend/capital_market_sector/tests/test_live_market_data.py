from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from capital_market_sector import client
from capital_market_sector.models import (
    Citation,
    DataFreshness,
    IndiaVixRecord,
    NiftySnapshotRecord,
)
from capital_market_sector.parsers import parse_gsec_yields


def _chart_payload() -> dict:
    timestamps = [
        int(datetime(2026, 10, 1, 15, tzinfo=ZoneInfo("Asia/Kolkata")).timestamp()),
        int(datetime(2026, 10, 2, 15, tzinfo=ZoneInfo("Asia/Kolkata")).timestamp()),
    ]
    return {
        "chart": {
            "result": [{
                "meta": {
                    "shortName": "NIFTY 50",
                    "chartPreviousClose": 99.0,
                },
                "timestamp": timestamps,
                "indicators": {
                    "quote": [{
                        "open": [99.5, 100.5],
                        "high": [101.0, 103.0],
                        "low": [98.0, 100.0],
                        "close": [100.0, 102.0],
                        "volume": [1000, 1200],
                    }]
                },
            }],
            "error": None,
        }
    }


@pytest.mark.asyncio
async def test_nifty_fetch_parses_and_persists_yahoo_snapshot(monkeypatch):
    persisted = []
    monkeypatch.setattr(client.db, "initialise_schema", lambda: None)
    monkeypatch.setattr(
        client.db,
        "upsert_rows",
        lambda table, rows: persisted.extend((table, row) for row in rows) or len(rows),
    )
    monkeypatch.setattr(client.db, "log_fetch", lambda *args, **kwargs: None)
    monkeypatch.setattr(client.db, "query_latest_rows", lambda *_args, **_kwargs: [])

    async def fetch_json(_client, _url, _params):
        return _chart_payload()

    monkeypatch.setattr(client, "_fetch_json", fetch_json)
    records = await client.fetch_nifty_snapshot()

    assert len(records) == 2
    assert isinstance(records[0], NiftySnapshotRecord)
    assert records[0].close_price == 102.0
    assert records[0].change_points == 2.0
    assert records[0].change_pct == pytest.approx(2.0)
    assert records[0].citation.freshness is DataFreshness.UPSTREAM_SNAPSHOT
    assert "query1.finance.yahoo.com" in records[0].citation.retrieval_url
    assert persisted[0][0] == "nifty_snapshot"


@pytest.mark.asyncio
async def test_vix_fetch_uses_same_verified_chart_contract(monkeypatch):
    monkeypatch.setattr(client.db, "initialise_schema", lambda: None)
    monkeypatch.setattr(client.db, "query_latest_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(client.db, "upsert_rows", lambda _table, rows: len(rows))
    monkeypatch.setattr(client.db, "log_fetch", lambda *args, **kwargs: None)

    async def fetch_json(_client, _url, _params):
        return _chart_payload()

    monkeypatch.setattr(client, "_fetch_json", fetch_json)
    records = await client.fetch_india_vix()

    assert len(records) == 2
    assert isinstance(records[0], IndiaVixRecord)
    assert records[0].vix_close == 102.0
    assert records[0].vix_change_pct == pytest.approx(2.0)
    assert records[0].citation.freshness is DataFreshness.UPSTREAM_SNAPSHOT


def test_chart_rejects_empty_or_error_payload():
    with pytest.raises(ValueError, match="no chart observations"):
        client._parse_market_chart(
            {"chart": {"result": [], "error": None}},
            symbol="^NSEI",
            document_title="test",
            retrieval_url="https://example.invalid/chart",
            is_vix=False,
        )


@pytest.mark.asyncio
async def test_recent_nifty_cache_avoids_repeated_provider_call(monkeypatch):
    row = {
        "period": "2026-10-02",
        "index_name": "NIFTY 50",
        "close_price": 25000.0,
        "citation": {
            "source_agent": "capital_market_sector",
            "source_authority": "Yahoo Finance",
            "document_title": "NIFTY 50 chart",
            "table_reference": "Yahoo Finance chart symbol ^NSEI",
            "retrieval_url": "https://query1.finance.yahoo.com/",
            "observation_period": "2026-10-02",
            "freshness": "upstream_snapshot",
        },
        "fetched_at": datetime.now().astimezone(),
    }
    monkeypatch.setattr(client.db, "initialise_schema", lambda: None)
    monkeypatch.setattr(client.db, "query_latest_rows", lambda *_args, **_kwargs: [row])

    async def should_not_fetch(*_args, **_kwargs):
        pytest.fail("A recent DuckDB snapshot should be reused.")

    monkeypatch.setattr(client, "_fetch_yahoo_chart", should_not_fetch)
    records = await client.fetch_nifty_snapshot()

    assert records[0].close_price == 25000.0
    assert records[0].citation.freshness is DataFreshness.CACHED


@pytest.mark.asyncio
async def test_market_breadth_uses_nse_mcp_and_persists_result(monkeypatch):
    payload = {
        "date": "2026-10-01",
        "total_stocks": 3712,
        "advances": 883,
        "declines": 2714,
        "unchanged": 115,
        "ad_ratio": 0.33,
        "total_volume": 5699843092,
    }
    calls = []
    persisted = []

    async def fake_call(endpoint, tool_name, arguments):
        calls.append((endpoint, tool_name, arguments))
        return payload

    monkeypatch.setattr(client, "call_nse_tool", fake_call)
    monkeypatch.setattr(client.db, "initialise_schema", lambda: None)
    monkeypatch.setattr(client.db, "query_latest_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        client.db,
        "upsert_rows",
        lambda table, rows: persisted.extend((table, row) for row in rows) or len(rows),
    )
    monkeypatch.setattr(client.db, "log_fetch", lambda *args, **kwargs: None)

    records = await client.fetch_market_breadth()

    assert calls[0][1] == "get_market_breadth"
    assert calls[0][2]["date"]
    assert records[0].period == "2026-10-01"
    assert records[0].total_stocks == 3712
    assert records[0].total_volume == 5699843092
    assert records[0].citation.freshness is DataFreshness.UPSTREAM_SNAPSHOT
    assert persisted[0][0] == "market_breadth"


def test_gsec_parser_uses_labeled_rbi_maturity_columns():
    columns = ["src_file", "tab", "period", "row_no"] + [f"c{index}" for index in range(1, 14)]
    header = ["file.csv", "New Format", "full-history", 7, ""]
    header.extend(f"{years} Year{'s' if years != 1 else ''}" for years in range(1, 13))
    observation = [
        "file.csv", "New Format", "full-history", 8,
        "Aug-2026", 5.8771, 6.2919, 6.4153, 6.5325, 6.6359,
        6.7105, 6.7723, 6.8038, 6.9072, 6.9603, 6.9957, 7.0253,
    ]
    citation = Citation(
        source_authority="Reserve Bank of India (RBI), Database on Indian Economy (DBIE)",
        document_title="Month-end Yield of SGL Transactions in Government Dated Securities",
        table_reference="financial_markets.r217_month_end_yield_of_sgl_transactions_in_government_dated_se",
        retrieval_url="https://data-api.dbie.rbihub.in/api/tables/financial_markets/example/rows",
        observation_period="2026-08",
        freshness=DataFreshness.UPSTREAM_SNAPSHOT,
    )
    records = parse_gsec_yields(
        {"columns": columns, "rows": [header, observation]},
        citation_factory=lambda period: citation.model_copy(
            update={"observation_period": period}
        ),
    )

    assert len(records) == 1
    assert records[0].period == "2026-08"
    assert records[0].two_year_gsec_yield_pct == pytest.approx(6.2919)
    assert records[0].five_year_gsec_yield_pct == pytest.approx(6.6359)
    assert records[0].ten_year_gsec_yield_pct == pytest.approx(6.9603)
    assert records[0].yield_curve_spread_2s10s_bps == pytest.approx(66.84)
    assert records[0].citation.freshness is DataFreshness.UPSTREAM_SNAPSHOT


@pytest.mark.asyncio
async def test_gsec_client_fetches_rbi_source_and_persists_rows(monkeypatch):
    columns = ["src_file", "tab", "period", "row_no"] + [f"c{index}" for index in range(1, 14)]
    rows = [
        ["file.csv", "New Format", "full-history", 7, ""]
        + [f"{years} Year{'s' if years != 1 else ''}" for years in range(1, 13)],
        ["file.csv", "New Format", "full-history", 8, "Aug-2026", 5.8771, 6.2919,
         6.4153, 6.5325, 6.6359, 6.7105, 6.7723, 6.8038, 6.9072, 6.9603, 6.9957, 7.0253],
    ]
    persisted = []
    monkeypatch.setattr(client.db, "initialise_schema", lambda: None)
    monkeypatch.setattr(client.db, "query_latest_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        client.db,
        "upsert_rows",
        lambda table, records: persisted.extend((table, record) for record in records) or len(records),
    )
    monkeypatch.setattr(client.db, "log_fetch", lambda *args, **kwargs: None)

    async def fetch_json(_http_client, url, params):
        assert url == client._GSEC_YIELD_API_URL
        assert params["limit"] >= 1000
        return {"columns": columns, "rows": rows}

    monkeypatch.setattr(client, "_fetch_json", fetch_json)
    records = await client.fetch_gsec_yield_snapshot()

    assert records[0].period == "2026-08"
    assert records[0].ten_year_gsec_yield_pct == pytest.approx(6.9603)
    assert records[0].citation.table_reference.startswith("financial_markets.")
    assert persisted[0][0] == "gsec_yields"
