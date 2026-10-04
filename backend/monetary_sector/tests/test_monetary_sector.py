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
from monetary_sector import cache_loaders


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
        from monetary_sector.cache_loaders import _load_cache, _save_records

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


_ECO_PAYLOAD = {
    "data": {
        "policy_repo_rate": 5.25,
        "standing_deposit_facility_sdf": 5.0,
        "marginal_standing_facility_msf": 5.5,
        "bank_rate": 5.5,
        "cash_reserve_ratio_crr": 3.0,
        "statutory_liquidity_ratio_slr": 18.0,
        "stance": "Neutral",
        "rates_effective_from": "2026-08-05",
        "unit": "percent per annum (CRR/SLR: percent of NDTL/deposits)",
    },
    "provenance": {
        "source": "RBI monetary policy statement (curated snapshot)",
        "as_of": "2026-10-04T09:07:04.252130Z",
        "reference": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "note": "Curated offline snapshot, current as of RBI policy dated 2026-08-05.",
    },
}

_TAVILY_PAYLOAD = {
    "query": "RBI repo rate MPC meeting",
    "results": [
        {
            "url": "https://example.com/mpc",
            "title": "RBI holds repo rate at 5.25%",
            "content": "The MPC kept the repo rate unchanged at 5.25 per cent.",
            "score": 0.91,
        },
        {"url": "", "title": "No link item", "content": "skipped"},
    ],
}


class TestMonetaryMCPWiring:
    @pytest.mark.asyncio
    async def test_eco_policy_rates_map_to_live_record(self, monkeypatch):
        from monetary_sector import client

        async def fake_call(*_args, **_kwargs):
            return _ECO_PAYLOAD

        monkeypatch.setattr(client, "_call_eco_policy_tool", fake_call)
        record = await client._fetch_policy_rates_from_eco_policy()

        assert record is not None
        assert record.repo_rate_pct == 5.25
        assert record.sdf_rate_pct == 5.0
        assert record.msf_rate_pct == 5.5
        assert record.crr_pct == 3.0
        assert record.corridor_width_bps == 50.0
        assert record.stance == "Neutral"
        assert record.rates_effective_from == "2026-08-05"
        assert record.citation.freshness == DataFreshness.LIVE
        assert record.citation.table_reference == "eco-policy:rbi_get_policy_rates"

    @pytest.mark.asyncio
    async def test_eco_policy_returns_none_without_repo_rate(self, monkeypatch):
        from monetary_sector import client

        async def fake_call(*_args, **_kwargs):
            raise TimeoutError("spawn failed")

        monkeypatch.setattr(client, "_call_eco_policy_tool", fake_call)
        assert await client._fetch_policy_rates_from_eco_policy() is None

        async def fake_empty(*_args, **_kwargs):
            return {"data": {"stance": "Neutral"}, "provenance": {}}

        monkeypatch.setattr(client, "_call_eco_policy_tool", fake_empty)
        assert await client._fetch_policy_rates_from_eco_policy() is None

    @pytest.mark.asyncio
    async def test_tavily_news_maps_items_and_never_raises(self, monkeypatch):
        import httpx
        from unittest.mock import patch
        from monetary_sector import client
        from monetary_sector.config import monetary_settings

        monkeypatch.setattr(monetary_settings, "TVLY_KEY_1", "test-key")

        async def fake_post(self_inner, url, **kwargs):
            assert url == "https://api.tavily.com/search"
            return httpx.Response(200, json=_TAVILY_PAYLOAD)

        with patch.object(httpx.AsyncClient, "post", fake_post):
            items = await client.fetch_mpc_news_via_tavily_mcp("MPC decision")
        assert len(items) == 1
        assert items[0]["title"] == "RBI holds repo rate at 5.25%"
        assert items[0]["url"] == "https://example.com/mpc"
        assert items[0]["source"] == "Tavily AI Search"

        async def fake_forbidden(self_inner, url, **kwargs):
            return httpx.Response(403, json={"error": "denied"})

        with patch.object(httpx.AsyncClient, "post", fake_forbidden):
            assert await client.fetch_mpc_news_via_tavily_mcp("MPC decision") == []

        async def fake_down(self_inner, url, **kwargs):
            raise httpx.ConnectError("no route")

        with patch.object(httpx.AsyncClient, "post", fake_down):
            assert await client.fetch_mpc_news_via_tavily_mcp("MPC decision") == []

    def test_news_gating(self):
        import monetary_sector.agent as agent_module

        assert agent_module._needs_mpc_news("What is the stance?", {"monetary_stance"})
        assert agent_module._needs_mpc_news("Latest MPC news please", {"policy_rates"})
        assert not agent_module._needs_mpc_news("What is the repo rate?", {"policy_rates"})
        assert not agent_module._needs_mpc_news("M3 growth?", {"money_supply"})

    @pytest.mark.asyncio
    async def test_agent_enriches_stance_queries_with_news(self, monkeypatch):
        import monetary_sector.agent as agent_module

        async def fake_fetch():
            return [{
                "period": "test-period",
                "repo_rate_pct": 5.25,
                "citation": {"freshness": "cached"},
            }]

        for name in agent_module._FETCHERS:
            monkeypatch.setitem(agent_module._FETCHERS, name, fake_fetch)

        async def fake_select(**_kwargs):
            return {"monetary_stance"}, None

        captured = {}

        async def fake_reason(**kwargs):
            captured.update(kwargs)
            return "Evidence-based response."

        news_calls = []

        async def fake_news(query):
            news_calls.append(query)
            return [{"title": "t", "url": "https://example.com", "snippet": "s", "date": None}]

        monkeypatch.setattr(agent_module, "select_relevant_services_with_llm", fake_select)
        monkeypatch.setattr(agent_module, "reason_over_sector_data", fake_reason)
        monkeypatch.setattr("monetary_sector.client.fetch_mpc_news_via_tavily_mcp", fake_news)

        result = await agent_module.monetary_agent_node({"query": "Explain the MPC stance"})
        assert news_calls, "stance queries must pull Tavily news"
        assert captured["data_context"]["realtime_mpc_news"][0]["title"] == "t"
        assert result["monetary_sector_news"][0]["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_agent_skips_news_for_plain_data_queries(self, monkeypatch):
        import monetary_sector.agent as agent_module

        async def fake_fetch():
            return [{
                "period": "test-period",
                "repo_rate_pct": 5.25,
                "citation": {"freshness": "cached"},
            }]

        for name in agent_module._FETCHERS:
            monkeypatch.setitem(agent_module._FETCHERS, name, fake_fetch)

        async def fake_select(**_kwargs):
            return {"policy_rates"}, None

        async def fail_if_called(_query):
            raise AssertionError("news fetch must be skipped for plain data queries")

        async def fake_reason(**kwargs):
            return "Evidence-based response."

        monkeypatch.setattr(agent_module, "select_relevant_services_with_llm", fake_select)
        monkeypatch.setattr(agent_module, "reason_over_sector_data", fake_reason)
        monkeypatch.setattr(
            "monetary_sector.client.fetch_mpc_news_via_tavily_mcp", fail_if_called
        )

        result = await agent_module.monetary_agent_node({"query": "What is the repo rate?"})
        assert result["monetary_sector_news"] == []


class TestMonetaryForceLive:
    def test_detects_explicit_live_requests(self):
        import monetary_sector.agent as agent_module

        assert agent_module._wants_force_live("Fetch LIVE repo rate data")
        assert agent_module._wants_force_live("Give me real-time rates")
        assert agent_module._wants_force_live("I want fresh data, up to date")
        assert not agent_module._wants_force_live("What is the repo rate?")
        assert not agent_module._wants_force_live("Explain the MPC stance")

    @pytest.mark.asyncio
    async def test_forced_fetch_bypasses_cache(self, temp_db, valid_citation, monkeypatch):
        """With force_live, MCP failure raises even when cached rows exist;
        without it, the cached row is served."""
        from monetary_sector import client
        from monetary_sector.client import MonetaryDataUnavailableError
        from monetary_sector.models import PolicyRatesRecord

        cache_loaders._save_records(
            "policy_rates",
            [PolicyRatesRecord(period="cached-period", repo_rate_pct=6.0, citation=valid_citation)],
            "test_policy_rates",
        )

        async def fake_no_eco():
            return None

        async def fake_live_fail(*_args, **_kwargs):
            raise TimeoutError("MCP down")

        monkeypatch.setattr(client, "_fetch_policy_rates_from_eco_policy", fake_no_eco)
        monkeypatch.setattr(client, "_fetch_live_records", fake_live_fail)

        with pytest.raises(MonetaryDataUnavailableError):
            await client.fetch_policy_rates(force_live=True)

        rows = await client.fetch_policy_rates(force_live=False)
        assert rows[0].period == "cached-period"
        assert rows[0].citation.freshness == DataFreshness.CACHED

    @pytest.mark.asyncio
    async def test_agent_forces_live_fetchers_on_explicit_request(self, monkeypatch):
        import monetary_sector.agent as agent_module

        seen = {}

        async def fake_live_fetch(lookback_months=12, *, force_live=False):
            seen["force_live"] = force_live
            return [{
                "period": "live-period",
                "repo_rate_pct": 5.25,
                "citation": {"freshness": "live"},
            }]

        async def fail_if_fetcher_used():
            raise AssertionError("forced path must not use _FETCHERS lambdas")

        for name in agent_module._FETCHERS:
            monkeypatch.setitem(agent_module._FETCHERS, name, fail_if_fetcher_used)

        async def fake_select(**_kwargs):
            return {"policy_rates"}, None

        async def fake_reason(**kwargs):
            return "Evidence-based response."

        async def fake_no_news(_query):
            return []

        monkeypatch.setattr(agent_module, "select_relevant_services_with_llm", fake_select)
        monkeypatch.setattr(agent_module, "reason_over_sector_data", fake_reason)
        monkeypatch.setattr(
            "monetary_sector.client.fetch_policy_rates", fake_live_fetch
        )
        monkeypatch.setattr(
            "monetary_sector.client.fetch_mpc_news_via_tavily_mcp", fake_no_news
        )

        result = await agent_module.monetary_agent_node(
            {"query": "Fetch LIVE repo rate data now"}
        )
        assert seen.get("force_live") is True
        assert result["monetary_sector_force_live"] is True
        assert result["monetary_sector_freshness"] == {"policy_rates": "live"}


class TestMonetaryMCPTransport:
    @pytest.mark.asyncio
    async def test_eco_tool_call_via_sdk_stdio(self, monkeypatch):
        """_call_eco_policy_tool speaks MCP over SDK stdio and extracts payload."""
        from types import SimpleNamespace

        import mcp as mcp_module
        import mcp.client.stdio as stdio_module
        from monetary_sector import client

        seen = {}

        class FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def initialize(self):
                seen["initialized"] = True

            async def call_tool(self, name, arguments=None, **kwargs):
                seen["tool"] = (name, arguments)
                return SimpleNamespace(
                    structuredContent=None,
                    content=[SimpleNamespace(text=json.dumps(_ECO_PAYLOAD), type="text")],
                    isError=False,
                )

        def fake_stdio(params):
            seen["command"] = params.command
            seen["has_env"] = params.env is None or isinstance(params.env, dict)

            class FakeCM:
                async def __aenter__(self):
                    return (object(), object())

                async def __aexit__(self, *args):
                    return False

            return FakeCM()

        monkeypatch.setattr(stdio_module, "stdio_client", fake_stdio)
        monkeypatch.setattr(mcp_module, "ClientSession", lambda *a, **k: FakeSession())

        payload = await client._call_eco_policy_tool()
        assert payload == _ECO_PAYLOAD
        assert seen["initialized"] is True
        assert seen["tool"] == ("rbi_get_policy_rates", {})
        assert seen["command"] == "uvx"
        assert seen["has_env"] is True

    @pytest.mark.asyncio
    async def test_eco_tool_call_reports_tool_error(self, monkeypatch):
        from types import SimpleNamespace

        import mcp as mcp_module
        import mcp.client.stdio as stdio_module
        from monetary_sector import client

        class FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def initialize(self):
                pass

            async def call_tool(self, name, arguments=None, **kwargs):
                return SimpleNamespace(
                    structuredContent=None, content=[], isError=True
                )

        class FakeCM:
            async def __aenter__(self):
                return (object(), object())

            async def __aexit__(self, *args):
                return False

        monkeypatch.setattr(stdio_module, "stdio_client", lambda params: FakeCM())
        monkeypatch.setattr(mcp_module, "ClientSession", lambda *a, **k: FakeSession())

        with pytest.raises(ValueError):
            await client._call_eco_policy_tool()



class TestMonetaryMCPRegistry:
    def test_keyword_routing_retrieves_only_necessary_functions(self):
        from monetary_sector import mcp_registry

        assert mcp_registry.match_services("What is the repo rate?") == {"policy_rates"}
        assert mcp_registry.match_services("M3 broad money growth?") == {"money_supply"}
        assert mcp_registry.match_services("Explain the MPC stance") == {"monetary_stance"}
        assert mcp_registry.match_services("How are things going?") == set()

    def test_dependencies_expand_stance_to_rates(self):
        from monetary_sector import mcp_registry

        assert mcp_registry.expand_dependencies({"monetary_stance"}) == {
            "monetary_stance", "policy_rates",
        }
        assert mcp_registry.expand_dependencies({"policy_rates"}) == {"policy_rates"}
        assert mcp_registry.expand_dependencies(set()) == set()

    def test_upstream_catalog_documents_wiring_verdicts(self):
        from monetary_sector import mcp_registry

        servers = mcp_registry.UPSTREAM_MCP_SERVERS
        assert servers["eco-policy"]["wired"] is True
        assert servers["dbie"]["wired"] is True
        assert servers["tavily-direct"]["wired"] is True
        assert servers["finstack"]["wired"] is False
        assert "rbi_get_policy_rates" in servers["eco-policy"]["tools"]

    def test_agent_keywords_come_from_registry(self):
        import monetary_sector.agent as agent_module
        from monetary_sector import mcp_registry

        assert agent_module._SERVICE_KEYWORDS == {
            name: spec.triggers for name, spec in mcp_registry.MONETARY_TOOLS.items()
        }


class TestStanceDerivation:
    def test_derive_and_save_stance_snapshot(self, temp_db, valid_citation):
        from monetary_sector import client, database
        from monetary_sector.models import PolicyRatesRecord

        record = PolicyRatesRecord(
            period="2026-08-05", repo_rate_pct=5.25, stance="Neutral",
            citation=valid_citation,
        )
        out = client.derive_and_save_stance_snapshot([record])
        assert out is not None
        assert out.repo_rate_pct == 5.25
        assert out.stance_label == "Neutral"
        assert out.period == "2026-08-05"
        assert client.derive_and_save_stance_snapshot([]) is None
        assert client.derive_and_save_stance_snapshot([{"nope": 1}]) is None
        with database.get_connection() as con:
            saved = con.execute(
                "SELECT repo_rate_pct FROM monetary_stance"
            ).fetchall()
        assert saved and saved[0][0] == 5.25

    @pytest.mark.asyncio
    async def test_agent_derives_stance_without_second_rates_pull(
        self, temp_db, valid_citation, monkeypatch
    ):
        """Stance reuses the fetched rates: the standalone stance fetcher must
        never run when rates succeeded (one live pull per query)."""
        import monetary_sector.agent as agent_module
        from monetary_sector.models import PolicyRatesRecord

        rate_record = PolicyRatesRecord(
            period="2026-08-05", repo_rate_pct=5.25, stance="Neutral",
            citation=valid_citation,
        )

        async def fake_rates():
            return [rate_record]

        async def fail_if_stance_fetched():
            raise AssertionError("stance must derive from rates, not refetch")

        async def fake_no_news(_query):
            return []

        async def fake_reason(**kwargs):
            return "Evidence-based response."

        monkeypatch.setitem(agent_module._FETCHERS, "policy_rates", fake_rates)
        monkeypatch.setitem(agent_module._FETCHERS, "monetary_stance", fail_if_stance_fetched)
        monkeypatch.setattr(agent_module, "reason_over_sector_data", fake_reason)
        monkeypatch.setattr(
            "monetary_sector.client.fetch_mpc_news_via_tavily_mcp", fake_no_news
        )

        result = await agent_module.monetary_agent_node({
            "query": "Repo rate and stance?",
            "_selected_services": {"monetary_stance"},
        })
        stance = result["monetary_sector_data"]["monetary_stance"]
        assert stance["repo_rate_pct"] == 5.25
        assert stance["stance_label"] == "Neutral"
        assert result["monetary_sector_freshness"]["monetary_stance"] != "unavailable"

    @pytest.mark.asyncio
    async def test_agent_falls_back_to_stance_fetcher_when_rates_fail(
        self, monkeypatch
    ):
        """Rates down: the standalone stance fetcher still serves from its own chain."""
        import monetary_sector.agent as agent_module

        async def fake_rates_fail():
            raise RuntimeError("eco down")

        async def fake_stance_fallback():
            return [{
                "period": "cached-period",
                "repo_rate_pct": 5.0,
                "citation": {"freshness": "cached"},
            }]

        async def fake_no_news(_query):
            return []

        async def fake_reason(**kwargs):
            return "Evidence-based response."

        monkeypatch.setitem(agent_module._FETCHERS, "policy_rates", fake_rates_fail)
        monkeypatch.setitem(agent_module._FETCHERS, "monetary_stance", fake_stance_fallback)
        monkeypatch.setattr(agent_module, "reason_over_sector_data", fake_reason)
        monkeypatch.setattr(
            "monetary_sector.client.fetch_mpc_news_via_tavily_mcp", fake_no_news
        )

        result = await agent_module.monetary_agent_node({
            "query": "Stance please",
            "_selected_services": {"monetary_stance"},
        })
        assert result["monetary_sector_data"]["monetary_stance"]["repo_rate_pct"] == 5.0
        assert any("policy_rates" in error for error in result["monetary_sector_errors"])


class TestMonetaryReasoningBudget:
    @pytest.mark.asyncio
    async def test_agent_uses_configured_output_budget_and_structured_prompt(self, monkeypatch):
        """The agent must forward MONETARY_LLM_MAX_TOKENS and a response contract
        (executive answer, mechanism analysis, observations table, takeaways,
        provenance) so answers are long, detailed, and reasoned like capital's."""
        import monetary_sector.agent as agent_module
        from monetary_sector.config import monetary_settings

        async def fake_fetch():
            return [{
                "period": "test-period",
                "repo_rate_pct": 5.25,
                "citation": {"freshness": "cached"},
            }]

        for name in agent_module._FETCHERS:
            monkeypatch.setitem(agent_module._FETCHERS, name, fake_fetch)

        async def fake_select(**_kwargs):
            return {"policy_rates"}, None

        captured = {}

        async def fake_reason(**kwargs):
            captured.update(kwargs)
            return "Evidence-based response."

        monkeypatch.setattr(agent_module, "select_relevant_services_with_llm", fake_select)
        monkeypatch.setattr(agent_module, "reason_over_sector_data", fake_reason)

        result = await agent_module.monetary_agent_node({"query": "What is the repo rate?"})
        assert result["monetary_sector_analysis"] == "Evidence-based response."
        assert captured["max_tokens"] == monetary_settings.MONETARY_LLM_MAX_TOKENS
        assert captured["max_tokens"] > 2200
        for marker in (
            "Direct Executive Answer",
            "Mechanism Analysis",
            "Structured Observations Table",
            "Key Takeaways",
            "Limitations & Data Provenance",
            "cache age from the citation",
        ):
            assert marker in captured["system_prompt"]

    def test_default_reasoning_budget_is_unchanged(self):
        """Other sectors keep the shared 2200-token default."""
        import inspect
        from core import sector_reasoning

        assert inspect.signature(sector_reasoning.reason_over_sector_data).parameters[
            "max_tokens"
        ].default == 2200


class TestMonetaryFreshCacheTTL:
    @pytest.mark.asyncio
    async def test_fresh_cache_short_circuits_live_fetch(
        self, temp_db, valid_citation, monkeypatch
    ):
        """Rows fetched seconds ago are served with zero MCP spawns."""
        from monetary_sector import client
        from monetary_sector.models import PolicyRatesRecord

        cache_loaders._save_records(
            "policy_rates",
            [PolicyRatesRecord(period="fresh-period", repo_rate_pct=5.25, citation=valid_citation)],
            "get_policy_rates",
        )

        async def fail_if_called(*_args, **_kwargs):
            raise AssertionError("fresh cache must short-circuit all live transport")

        monkeypatch.setattr(client, "_fetch_policy_rates_from_eco_policy", fail_if_called)
        monkeypatch.setattr(client, "_fetch_live_records", fail_if_called)

        rows = await client.fetch_policy_rates(lookback_months=1)
        assert rows[0].period == "fresh-period"
        assert rows[0].citation.freshness == DataFreshness.CACHED

    @pytest.mark.asyncio
    async def test_stale_cache_goes_live(self, temp_db, valid_citation, monkeypatch):
        """Rows older than the TTL trigger a live MCP pull."""
        from datetime import timedelta
        from monetary_sector import client, database
        from monetary_sector.models import PolicyRatesRecord

        live_record = PolicyRatesRecord(
            period="live-period", repo_rate_pct=5.25, citation=valid_citation
        )
        old_fetched_at = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        database.upsert_rows(
            "policy_rates",
            [{
                "period": "stale-period",
                "repo_rate_pct": 6.0,
                "citation": valid_citation.model_dump_json(),
                "fetched_at": old_fetched_at,
            }],
        )

        async def fake_no_eco():
            return None

        async def fake_live(*_args, **_kwargs):
            return [live_record]

        monkeypatch.setattr(client, "_fetch_policy_rates_from_eco_policy", fake_no_eco)
        monkeypatch.setattr(client, "_fetch_live_records", fake_live)

        rows = await client.fetch_policy_rates(lookback_months=1)
        assert rows[0].period == "live-period"

    @pytest.mark.asyncio
    async def test_force_live_bypasses_fresh_ttl(self, temp_db, valid_citation, monkeypatch):
        """An explicit live request ignores even a seconds-old cache."""
        from monetary_sector import client
        from monetary_sector.client import MonetaryDataUnavailableError
        from monetary_sector.models import PolicyRatesRecord

        cache_loaders._save_records(
            "policy_rates",
            [PolicyRatesRecord(period="fresh-period", repo_rate_pct=5.0, citation=valid_citation)],
            "get_policy_rates",
        )

        async def fake_no_eco():
            return None

        async def fake_live_fail(*_args, **_kwargs):
            raise TimeoutError("MCP down")

        monkeypatch.setattr(client, "_fetch_policy_rates_from_eco_policy", fake_no_eco)
        monkeypatch.setattr(client, "_fetch_live_records", fake_live_fail)

        with pytest.raises(MonetaryDataUnavailableError):
            await client.fetch_policy_rates(lookback_months=1, force_live=True)


class TestMonetaryCacheClear:
    def test_clear_deletes_data_rows_but_preserves_audit(
        self, temp_db, valid_citation
    ):
        from monetary_sector import client, database
        from monetary_sector.models import PolicyRatesRecord

        cache_loaders._save_records(
            "policy_rates",
            [PolicyRatesRecord(period="p1", repo_rate_pct=5.0, citation=valid_citation)],
            "get_policy_rates",
        )
        cleared = database.clear_cached_tables()
        assert cleared["policy_rates"] == 1
        assert cleared["money_supply"] == 0
        assert set(cleared) == {
            "policy_rates", "money_supply", "system_liquidity", "monetary_stance",
        }
        with database.get_connection() as con:
            remaining = con.execute("SELECT COUNT(*) FROM policy_rates").fetchone()[0]
            log_rows = con.execute(
                "SELECT tool_name, status FROM fetch_log WHERE tool_name = 'clear_monetary_cache'"
            ).fetchall()
        assert remaining == 0
        assert log_rows and log_rows[0][1] == "cache_cleared"

    def test_clear_rejects_unknown_and_audit_tables(self, temp_db):
        from monetary_sector import database

        with pytest.raises(ValueError):
            database.clear_cached_tables(["drop_table"])
        with pytest.raises(ValueError):
            database.clear_cached_tables(["fetch_log"])

    @pytest.mark.asyncio
    async def test_mcp_news_tool_returns_typed_response(self, monkeypatch):
        import httpx
        from unittest.mock import patch
        from monetary_sector.config import monetary_settings
        from monetary_sector.mcp_server import get_realtime_monetary_news

        monkeypatch.setattr(monetary_settings, "TVLY_KEY_1", "test-key")

        async def fake_post(self_inner, url, **kwargs):
            return httpx.Response(200, json=_TAVILY_PAYLOAD)

        with patch.object(httpx.AsyncClient, "post", fake_post):
            result = await get_realtime_monetary_news(
                query="MPC decision", max_results=5
            )
        assert result.status == DataFreshness.LIVE
        assert result.total_results == 1
        assert result.news_items[0].title == "RBI holds repo rate at 5.25%"
        assert result.news_items[0].source == "Tavily AI Search"

    @pytest.mark.asyncio
    async def test_mcp_tool_clears_cache(self, temp_db, valid_citation):
        from monetary_sector import client
        from monetary_sector.mcp_server import clear_monetary_cache
        from monetary_sector.models import PolicyRatesRecord

        cache_loaders._save_records(
            "policy_rates",
            [PolicyRatesRecord(period="p1", repo_rate_pct=5.0, citation=valid_citation)],
            "get_policy_rates",
        )
        result = await clear_monetary_cache()
        assert result.status == "cache_cleared"
        assert result.cleared_tables["policy_rates"] == 1
        assert result.total_rows_deleted >= 1
        assert "unavailable" in result.message

    @pytest.mark.asyncio
    async def test_api_delete_cache(self, temp_db, valid_citation):
        from httpx import AsyncClient, ASGITransport
        from monetary_sector import client
        from monetary_sector.api.app import app
        from monetary_sector.models import PolicyRatesRecord

        cache_loaders._save_records(
            "policy_rates",
            [PolicyRatesRecord(period="p1", repo_rate_pct=5.0, citation=valid_citation)],
            "get_policy_rates",
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.delete("/cache")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "cache_cleared"
        assert body["cleared_tables"]["policy_rates"] == 1

    @pytest.mark.asyncio
    async def test_agent_handles_clear_cache_intent(self, monkeypatch):
        import monetary_sector.agent as agent_module

        async def fail_if_fetched(*_args, **_kwargs):
            raise AssertionError("clear-cache intent must not fetch any dataset")

        for name in agent_module._FETCHERS:
            monkeypatch.setitem(agent_module._FETCHERS, name, fail_if_fetched)

        result = await agent_module.monetary_agent_node({"query": "Please clear the cache"})
        assert "cleared" in result["monetary_sector_analysis"]
        assert result["monetary_sector_data"] == {}
        assert result["monetary_sector_freshness"] == {}
        assert result["monetary_sector_errors"] == []

    def test_clear_intent_detection(self):
        import monetary_sector.agent as agent_module

        assert agent_module._wants_cache_clear("clear the cache please")
        assert agent_module._wants_cache_clear("Reset cache and retry")
        assert not agent_module._wants_cache_clear("What is the repo rate?")
        assert not agent_module._wants_cache_clear("Fetch LIVE repo rate data")
