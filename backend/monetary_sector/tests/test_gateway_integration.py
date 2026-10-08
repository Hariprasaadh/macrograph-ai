from __future__ import annotations

import json

from fastapi.testclient import TestClient
from api import chat_helpers


def test_gateway_import_initializes_sector_schemas():
    import main as gateway
    from capital_market_sector import database as capital_database
    from external_sector import database as external_database
    from labour_sector import database as labour_database
    from monetary_sector import database as monetary_database

    assert gateway.app is not None
    expected_tables = {
        external_database: {"forex_reserves", "trade_balance", "bop", "exchange_rates", "external_flows", "fetch_log"},
        labour_database: {"unemployment", "lfpr", "wpr", "labour_conditions", "fetch_log"},
        capital_database: {"nifty_snapshot", "market_history", "india_vix", "market_breadth", "gsec_yields", "fetch_log"},
        monetary_database: {"policy_rates", "money_supply", "system_liquidity", "monetary_stance", "fetch_log"},
    }
    for database, expected in expected_tables.items():
        with database.get_connection() as connection:
            tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        assert expected <= tables


def test_sector_stream_retains_citation_metadata(monkeypatch):
    import main as gateway
    seen_selection = {}

    async def select_policy_rates(**kwargs):
        seen_selection.update(kwargs)
        return {"policy_rates"}, None

    async def fake_response(_target: str, _message: str, **kwargs) -> dict:
        assert kwargs["selected_services"] == {"policy_rates"}
        return {
            "status": "partial",
            "agent_routed": "Monetary & Liquidity Specialist",
            "full_report": "Monetary data report.",
            "data_context": {},
            "freshness": {"policy_rates": "upstream_snapshot"},
            "errors": [],
            "citations": [{
                "source_agent": "monetary_sector",
                "source_authority": "Reserve Bank of India (RBI)",
                "table_reference": "/banking/select-economic-indicators",
                "retrieval_url": "https://dbie.rbihub.in/banking/select-economic-indicators",
                "observation_period": "test-period",
                "freshness": "upstream_snapshot",
                "source_note": "Deployment last-scrape note.",
                "frequency": "Monthly",
                "unit": "%",
            }],
        }

    import api.chat as chat_api
    monkeypatch.setattr(chat_api, "select_relevant_services_with_llm", select_policy_rates)
    monkeypatch.setattr(chat_api, "_run_direct_sector_chat", fake_response)
    with TestClient(gateway.app) as client:
        response = client.post(
            "/api/v1/chat/stream",
            json={"agent": "monetary_sector", "message": "test"},
        )

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data:").strip())
        for line in response.text.splitlines()
        if line.startswith("data:")
    ]
    done = next(event for event in reversed(events) if event.get("type") == "done")
    assert done["citations"][0]["table_reference"] == "/banking/select-economic-indicators"
    assert done["citations"][0]["source_note"] == "Deployment last-scrape note."
    assert done["citations"][0]["frequency"] == "Monthly"
    steps = [event for event in events if event.get("type") == "step"]
    assert any(event["title"] == "Retrieving policy rates" for event in steps)
    assert any(event["title"] == "Preparing evidence-based explanation" for event in steps)
    assert seen_selection["query"] == "test"


def test_sector_response_maps_full_provenance():
    import main as gateway

    citation = {
        "source_agent": "monetary_sector",
        "source_authority": "Reserve Bank of India (RBI)",
        "document_title": "Select Economic Indicators",
        "table_reference": "/banking/select-economic-indicators",
        "retrieval_url": "https://dbie.rbihub.in/banking/select-economic-indicators",
        "source_base_url": "https://dbie.rbihub.in",
        "source_note": "Deployment last-scrape note.",
        "as_of": None,
        "frequency": "Monthly",
        "unit": "%",
        "observation_period": "test-period",
        "freshness": "upstream_snapshot",
        "dataset": "policy_rates",
    }
    response = chat_helpers._sector_chat_response(
        "monetary_sector",
        {
            "monetary_sector_data": {},
            "monetary_sector_freshness": {},
            "monetary_sector_errors": [],
            "monetary_sector_citations": [citation],
        },
    )

    assert response["citations"][0]["source_note"] == "Deployment last-scrape note."
    assert response["citations"][0]["source_base_url"] == "https://dbie.rbihub.in"
    assert response["citations"][0]["unit"] == "%"


def test_sector_report_preserves_markdown_structure_and_selected_data_only():
    import main as gateway

    response = chat_helpers._sector_chat_response(
        "labour_sector",
        {
            "labour_sector_analysis": (
                "## Unemployment observations\n\n"
                "- The reported rate is 5.4% for 2026-08."
            ),
            "labour_sector_data": {
                "unemployment": {
                    "period": "2026-08",
                    "unemployment_rate_pct": 5.4,
                }
            },
            "labour_sector_freshness": {"unemployment": "live"},
            "labour_sector_errors": [],
            "labour_sector_citations": [],
        },
    )

    assert "## Unemployment observations" in response["full_report"]
    assert "5.4%" in response["full_report"]
    assert "Policy rates" not in response["full_report"]
    assert set(response["freshness"]) == {"unemployment"}
    assert response["status"] == "completed"


def test_missing_llm_fallback_formats_observations_and_takeaways_as_tables():
    import main as gateway

    response = chat_helpers._sector_chat_response(
        "external_sector",
        {
            "external_sector_analysis": "",
            "external_sector_data": {
                "trade_balance": {
                    "period": "2026-07",
                    "exports_usd_bn": 44.2435,
                    "imports_usd_bn": 76.2232,
                    "trade_balance_usd_bn": -31.9798,
                }
            },
            "external_sector_freshness": {"trade_balance": "live"},
            "external_sector_errors": [
                "LLM reasoning unavailable: No sector-specific or shared GROQ_API_KEY is configured."
            ],
            "external_sector_citations": [{
                "dataset": "trade_balance",
                "source_authority": "Reserve Bank of India (RBI), Database on Indian Economy (DBIE)",
                "table_reference": "external_sector.r433_india_s_foreign_trade_us_dollars",
                "freshness": "live",
            }],
        },
    )

    report = response["full_report"]
    assert "| Indicator | Observation | Period | Freshness | Source |" in report
    assert "| Insight | Implication |" in report
    assert "Imports exceeded exports in the reported period" in report
    assert "Model-generated analysis was unavailable" in report
    assert response["status"] == "partial"
