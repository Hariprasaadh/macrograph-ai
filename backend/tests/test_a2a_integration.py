"""Integration tests: real registry/bootstrap and handlers, with upstream data fetchers patched."""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.orchestrator.registry_bootstrap  # noqa: F401  registers all sector agents
from core.orchestrator import graph as orchestrator_graph
from core.orchestrator.a2a_dispatch import aggregate, delegate
from core.protocols.a2a import A2AClient, agent_registry, trace_store
from core.protocols.a2a.api import router as a2a_router
from core.protocols.a2a.dependencies import CROSS_SECTOR_DEPENDENCIES
from core.protocols.a2a.exceptions import ErrorCode
from core.protocols.a2a.executor_adapter import SECTOR_ANALYSIS
from core.protocols.a2a.lifecycle import AgentExecutor
from core.protocols.a2a.models import A2AArtifact, A2AMessage, A2AMessagePart, TaskResponse, TaskState
from core.protocols.a2a.peers import gather_peer_context
from finance_sector import client as finance_client
from finance_sector.models import BankCreditGrowthRecord
from finance_sector.models import Citation as FinanceCitation
from monetary_sector import client as monetary_client
from monetary_sector.models import Citation as MonetaryCitation
from monetary_sector.models import PolicyRatesRecord


def conv() -> str:
    return f"conv-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def upstream(monkeypatch):
    """Patch every upstream data fetcher used by the peer-facing handlers."""
    async def policy_rates(lookback_months: int = 6):
        return [PolicyRatesRecord(period="2026-05", repo_rate_pct=5.25, citation=MonetaryCitation(
            document_title="RBI Policy Rates", table_reference="Table 43",
            retrieval_url="https://rbi.example/policy", observation_period="2026-05"))]

    async def credit(lookback_months: int = 12):
        return [BankCreditGrowthRecord(
            period="2026-04", gross_credit_cr=1.0e7, non_food_credit_cr=9.9e6, non_food_credit_yoy_pct=11.2,
            citation=FinanceCitation(
                source_authority="Reserve Bank of India", document_title="Sectoral Deployment of Bank Credit",
                table_reference="r539", retrieval_url="https://rbi.example/credit", observation_period="2026-04"))]

    async def prices_node(state: dict[str, Any]) -> dict[str, Any]:
        return {"prices_sector_errors": [], "prices_sector_data": {"observations": [{
            "value": 3.2, "unit": "% YoY", "observation_period": "2026-04", "retrieval_status": "live",
            "source_authority": "MoSPI", "dataset_reference": "CPI (Combined)", "indicator_id": "cpi_headline",
            "series_code": "CPI_COMBINED_HEADLINE", "url": "https://mospi.example/cpi",
            "retrieved_at": "2026-05-12T08:00:00+00:00"}]}}

    monkeypatch.setattr(monetary_client, "fetch_policy_rates", policy_rates)
    monkeypatch.setattr(finance_client, "fetch_bank_credit_growth", credit)
    import prices_sector.a2a_handlers as prices_handlers
    monkeypatch.setattr(prices_handlers, "prices_agent_node", prices_node)


class StubExecutor(AgentExecutor):
    """Stands in for a sector executor so no live data source is touched."""

    def __init__(self, artifacts: list[A2AArtifact] | None = None, fail: bool = False) -> None:
        self.artifacts = artifacts or []
        self.fail = fail

    async def execute(self, context, event_queue) -> TaskResponse:
        if self.fail:
            raise RuntimeError("upstream MCP unreachable")
        return TaskResponse(
            task_id=context.task_id, status=TaskState.COMPLETED, artifacts=self.artifacts,
            messages=[A2AMessage(role="agent", parts=[A2AMessagePart(kind="text", content="done")])],
        )

    async def cancel(self, context, event_queue) -> bool:
        return True


def stub(monkeypatch, agent_id: str, executor: StubExecutor) -> None:
    card = agent_registry.get_agent(agent_id)
    monkeypatch.setitem(agent_registry._executors, card.name, executor)


def finance_artifact() -> A2AArtifact:
    return A2AArtifact(name="Finance Sector Analysis", type="markdown", content="# Finance\nCredit growth 11.2%")


def monetary_artifact() -> A2AArtifact:
    return A2AArtifact(
        name="monetary_report", type="json",
        content={"policy": {"indicators": {"repo_rate": {
            "latest_value": 5.25, "unit": "%", "latest_period": "2026-05", "data_status": "live"}}},
            "citations": [{"source_authority": "RBI DBIE", "table": "Table 43", "period": "2026-05"}]},
    )


# ------------------------------------------------------------------ registry wiring
class TestBootstrap:
    def test_all_ten_sector_agents_registered_with_ids_and_sector_analysis(self):
        ids = set(agent_registry.agent_ids())
        assert ids == {
            "real_sector", "prices_sector", "monetary_sector", "finance_sector", "fiscal_sector",
            "external_sector", "capital_market_sector", "agriculture_sector", "labour_sector", "services_sector",
        }
        for agent_id in ids:
            card = agent_registry.get_agent(agent_id)
            assert SECTOR_ANALYSIS in card.supported_tasks and "keywords" in card.metadata

    def test_every_declared_dependency_has_a_provider_handler(self):
        for dep in CROSS_SECTOR_DEPENDENCIES:
            assert dep.task in agent_registry.get_agent(dep.provider).supported_tasks, dep


# ------------------------------------------------------------------ orchestrator -> sector agents
class TestOrchestratorDelegation:
    async def test_orchestrator_to_single_agent_with_typed_peer_task(self, upstream):
        cid = conv()
        resp = await A2AClient("orchestrator").send_request(
            "finance_sector", "bank_credit_growth", {}, conversation_id=cid)
        assert resp.status == "success"
        obs = resp.result["observations"][0]
        assert (obs["value"], obs["observation_period"]) == (11.2, "2026-04")
        src = resp.sources[0]
        assert (src.source_name, src.table, src.reporting_period) == ("Reserve Bank of India", "r539", "2026-04")
        assert src.source_url == "https://rbi.example/credit"

    async def test_orchestrator_to_finance_and_monetary_concurrently(self, monkeypatch):
        stub(monkeypatch, "finance_sector", StubExecutor([finance_artifact()]))
        stub(monkeypatch, "monetary_sector", StubExecutor([monetary_artifact()]))
        cid = conv()
        responses = await delegate("credit growth and repo rate", ["finance_sector", "monetary_sector"], cid)
        assert [r.status for r in responses] == ["success", "success"]

        merged = aggregate(responses)
        assert merged["status"] == "a2a_completed" and merged["a2a_errors"] == []
        assert {a["agent_id"] for a in merged["agent_analyses"]} == {"finance_sector", "monetary_sector"}
        [obs] = merged["collected_observations"]
        assert obs["indicator_id"] == "in.macro.monetary.repo_rate" and obs["value"] == 5.25
        # Provenance from the structured citation reached the orchestrator.
        assert any(s["agent"] == "monetary_sector" and s["table"] == "Table 43" for s in merged["a2a_sources"])

        nodes = trace_store.get_trace(cid)
        assert {n["receiver_agent"] for n in nodes} == {"finance_sector", "monetary_sector"}
        assert all(n["parent_request_id"] is None and n["sender_agent"] == "orchestrator" for n in nodes)

    async def test_failed_agent_yields_partial_result_not_a_crash(self, monkeypatch):
        stub(monkeypatch, "finance_sector", StubExecutor([finance_artifact()]))
        stub(monkeypatch, "monetary_sector", StubExecutor(fail=True))
        responses = await delegate("q", ["finance_sector", "monetary_sector"], conv())
        merged = aggregate(responses)
        assert merged["status"] == "a2a_partial"
        assert [e["agent"] for e in merged["a2a_errors"]] == ["monetary_sector"]
        assert merged["a2a_errors"][0]["code"] == ErrorCode.AGENT_ERROR.value
        assert [a["agent_id"] for a in merged["agent_analyses"]] == ["finance_sector"]

    async def test_unregistered_agent_is_reported_as_error(self):
        responses = await delegate("q", ["no_such_sector"], conv())
        assert aggregate(responses)["a2a_errors"][0]["code"] == "AGENT_NOT_FOUND"

    async def test_follow_up_requests_are_dispatched_with_parent_link(self, monkeypatch, upstream):
        from core.protocols.a2a.messages import FollowUp, HandlerOutput, SourceProvenance
        from core.protocols.a2a.server import TaskContract, a2a_server

        async def asks_for_repo_rate(request, ctx):
            return HandlerOutput(
                result={"note": "policy rate needed"}, sources=[SourceProvenance(source_name="Finance test")],
                follow_ups=[FollowUp(receiver_agent="monetary_sector", task="repo_rate",
                                     reason="needs policy rate")],
            )

        monkeypatch.setitem(a2a_server._contracts, ("finance_sector", SECTOR_ANALYSIS),
                            TaskContract(asks_for_repo_rate))
        cid = conv()
        first, follow = await delegate("lending rates", ["finance_sector"], cid)

        assert follow.sender_agent == "monetary_sector" and follow.status == "success"
        by_id = {n["request_id"]: n for n in trace_store.get_trace(cid)}
        assert by_id[follow.request_id]["parent_request_id"] == first.request_id
        assert by_id[follow.request_id]["depth"] == 1


# ------------------------------------------------------------------ sector -> sector
class TestSectorToSector:
    async def test_external_asks_monetary_and_prices(self, upstream):
        lines, records = await gather_peer_context("external_sector", None, "rupee pressure")
        text = "\n".join(lines)
        assert "RBI policy repo rate" in text and "5.25" in text and "Table 43" in text
        assert "Headline CPI inflation" in text and "3.2" in text
        assert {r["owner_agent"] for r in records} == {"monetary_sector", "prices_sector"}
        repo = next(r for r in records if r["indicator_id"] == "in.macro.monetary.repo_rate")
        assert repo["sources"][0]["source_url"] == "https://rbi.example/policy"

    async def test_fiscal_asks_finance_for_credit_and_peers_for_rates(self, upstream):
        lines, records = await gather_peer_context("fiscal_sector", None, "crowding out")
        assert {r["owner_agent"] for r in records} == {"monetary_sector", "prices_sector", "finance_sector"}
        credit = next(r for r in records if r["indicator_id"] == "in.macro.monetary.bank_credit_growth")
        assert credit["value"] == 11.2 and credit["sources"][0]["table"] == "r539"
        assert any("finance_sector via A2A" in line for line in lines)

    async def test_peer_requests_are_linked_to_the_calling_request(self, upstream):
        from core.protocols.a2a.executor_adapter import A2A_CONTEXT_KEY
        from core.protocols.a2a.messages import A2ACallContext

        cid = conv()
        ctx = A2ACallContext(conversation_id=cid, request_id="req-root", agent_id="external_sector",
                             depth=0, call_chain=("orchestrator", "external_sector"))
        await gather_peer_context("external_sector", {A2A_CONTEXT_KEY: ctx.model_dump(mode="json")}, "q")
        nodes = trace_store.get_trace(cid)
        assert len(nodes) == 2
        assert all(n["parent_request_id"] == "req-root" and n["depth"] == 1 for n in nodes)
        assert all(n["sender_agent"] == "external_sector" for n in nodes)

    async def test_failed_peer_degrades_gracefully(self, upstream, monkeypatch):
        async def broken(lookback_months: int = 6):
            raise ConnectionError("DBIE MCP down")

        monkeypatch.setattr(monetary_client, "fetch_policy_rates", broken)
        lines, records = await gather_peer_context("finance_sector", None, "q")
        text = "\n".join(lines)
        assert "Peer data unavailable from monetary_sector: DATA_SOURCE_ERROR" in text
        assert "Headline CPI inflation" in text  # the healthy peer is unaffected
        failed = next(r for r in records if r.get("status") == "unavailable")
        assert failed["errors"][0]["code"] == "DATA_SOURCE_ERROR"

    async def test_sector_cannot_call_undeclared_peer_or_task(self, upstream):
        monetary = A2AClient("monetary_sector", max_retries=0)
        resp = await monetary.send_request("external_sector", SECTOR_ANALYSIS, {"query": "x"})
        assert resp.error_codes == [ErrorCode.DEPENDENCY_NOT_ALLOWED]
        external = A2AClient("external_sector", max_retries=0)
        resp = await external.send_request("monetary_sector", SECTOR_ANALYSIS, {"query": "x"})
        assert resp.error_codes == [ErrorCode.DEPENDENCY_NOT_ALLOWED]

    async def test_finance_agent_node_requests_missing_inputs_over_a2a(self, upstream, monkeypatch):
        """The agent node asks Monetary and Prices over A2A instead of reading them from state."""
        import finance_sector.agent as finance_agent

        async def empty(*args, **kwargs):
            return []

        async def fake_news(query, max_results=4):
            return None

        async def fake_llm(*args, **kwargs):
            return "analysis"

        for name in ("fetch_asset_quality", "fetch_lending_rates", "fetch_deposits_and_cd_ratio"):
            monkeypatch.setattr(finance_client, name, empty)
        monkeypatch.setattr(finance_agent, "fetch_banking_market_indicators", empty)
        monkeypatch.setattr(finance_agent, "fetch_realtime_finance_news", fake_news)
        monkeypatch.setattr(finance_agent, "get_groq_client", lambda: object())
        monkeypatch.setattr(finance_agent, "_execute_groq_reasoning", fake_llm)

        result = await finance_agent.finance_agent_node({"query": "lending rates"})
        inputs = result["finance_sector_data"]["a2a_inputs"]
        assert inputs["repo_rate_from_monetary_sector"] == 5.25
        assert inputs["headline_cpi_from_prices_sector"] == 3.2
        assert {s["owner_agent"] for s in inputs["a2a_peer_signals"]} == {"monetary_sector", "prices_sector"}


# ------------------------------------------------------------------ full LangGraph flow
class TestOrchestratorGraph:
    def test_graph_routes_by_cards_delegates_over_a2a_and_reports_provenance(self, monkeypatch):
        stub(monkeypatch, "finance_sector", StubExecutor([finance_artifact()]))
        stub(monkeypatch, "monetary_sector", StubExecutor([monetary_artifact()]))
        monkeypatch.setattr(orchestrator_graph.llm_client, "complete", lambda *a, **k: "synthesis text")

        state = orchestrator_graph.macro_orchestrator_graph.invoke(
            {"query": "How are bank credit and the RBI repo rate evolving?", "status": "started"})

        assert set(state["routed_agents"]) == {"finance_sector", "monetary_sector"}
        assert state["routing_method"] == "lexical"
        assert state["status"] == "completed"
        assert state["conversation_id"] and state["a2a_errors"] == []
        assert {n["receiver_agent"] for n in state["a2a_trace"]} == {"finance_sector", "monetary_sector"}
        assert "A2A Source Provenance" in state["final_report"] and "Table 43" in state["final_report"]

    def test_graph_survives_a_failing_agent(self, monkeypatch):
        stub(monkeypatch, "finance_sector", StubExecutor(fail=True))
        stub(monkeypatch, "monetary_sector", StubExecutor([monetary_artifact()]))
        prompts: list[str] = []
        monkeypatch.setattr(orchestrator_graph.llm_client, "complete",
                            lambda prompt, *a, **k: prompts.append(prompt) or "synthesis")

        state = orchestrator_graph.macro_orchestrator_graph.invoke(
            {"query": "bank credit and repo rate", "status": "started"})

        assert state["status"] == "completed"
        assert [e["agent"] for e in state["a2a_errors"]] == ["finance_sector"]
        assert "could not respond" in prompts[0] and "finance_sector" in prompts[0]
        assert "Unavailable Agent Data" in state["final_report"]

    async def test_sync_node_works_inside_a_running_event_loop(self, monkeypatch):
        stub(monkeypatch, "monetary_sector", StubExecutor([monetary_artifact()]))
        out = orchestrator_graph.parallel_a2a_execute_node(
            {"query": "repo", "routed_agents": ["monetary_sector"], "conversation_id": conv()})
        assert out["status"] == "a2a_completed" and out["collected_observations"]

    async def test_legacy_target_sectors_still_select_agents(self, monkeypatch):
        stub(monkeypatch, "agriculture_sector", StubExecutor([A2AArtifact(
            name="Agriculture findings", type="json", content={"citations": [], "findings": []})]))
        out = await orchestrator_graph.parallel_a2a_execute_async(
            {"query": "wheat", "target_sectors": ["agriculture_rural"], "conversation_id": conv()})
        assert out["agent_analyses"][0]["agent"] == "Agriculture Agent"


# ------------------------------------------------------------------ HTTP surface
class TestHttpApi:
    @pytest.fixture
    def http(self, monkeypatch):
        from pydantic import SecretStr
        from core.config import settings
        monkeypatch.setattr(settings, "A2A_API_KEY", SecretStr(""))
        monkeypatch.setattr(settings, "A2A_ALLOW_ANONYMOUS_REQUESTS", True)
        app = FastAPI()
        app.include_router(a2a_router)
        return TestClient(app)

    def test_discovery_endpoints(self, http):
        agents = http.get("/a2a/v1/agents").json()["agents"]
        assert len(agents) == 10
        card = http.get("/a2a/v1/agents/monetary_sector").json()
        assert card["agent_id"] == "monetary_sector" and "repo_rate" in card["supported_tasks"]
        assert http.get("/a2a/v1/agents/nope").status_code == 404
        assert http.get("/a2a/v1/capabilities/bank_credit_growth").json()["agents"] == ["finance_sector"]

    def test_submit_request_and_inspect_trace(self, http, upstream):
        cid = conv()
        body = {"sender_agent": "gateway", "receiver_agent": "monetary_sector", "task": "repo_rate",
                "conversation_id": cid, "call_chain": ["gateway"]}
        response = http.post("/a2a/v1/requests", json=body)
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success" and payload["sources"][0]["table"] == "Table 43"
        trace = http.get(f"/a2a/v1/traces/{cid}").json()
        assert trace["requests"][0]["status"] == "success" and trace["tree"][0]["children"] == []
        assert http.get("/a2a/v1/traces/unknown").status_code == 404

    def test_protocol_failures_are_responses_and_identity_spoofing_is_blocked(self, http):
        body = {"sender_agent": "gateway", "receiver_agent": "ghost", "task": "x",
                "conversation_id": conv(), "call_chain": ["gateway"]}
        failed = http.post("/a2a/v1/requests", json=body).json()
        assert failed["status"] == "failed" and failed["errors"][0]["code"] == "AGENT_NOT_FOUND"
        spoof = {**body, "sender_agent": "external_sector", "call_chain": ["external_sector"]}
        assert http.post("/a2a/v1/requests", json=spoof).status_code == 403
        assert http.post("/a2a/v1/requests", json={"sender_agent": ""}).status_code == 422

    def test_api_key_is_enforced_when_configured(self, http, monkeypatch):
        from pydantic import SecretStr
        from core.config import settings
        monkeypatch.setattr(settings, "A2A_API_KEY", SecretStr("s3cret"))
        assert http.get("/a2a/v1/agents").status_code == 401
        assert http.get("/a2a/v1/agents", headers={"X-A2A-Key": "wrong"}).status_code == 401
        assert http.get("/a2a/v1/agents", headers={"X-A2A-Key": "s3cret"}).status_code == 200

    def test_submission_is_refused_when_no_key_and_anonymous_not_allowed(self, http, monkeypatch):
        from core.config import settings
        monkeypatch.setattr(settings, "A2A_ALLOW_ANONYMOUS_REQUESTS", False)
        body = {"sender_agent": "gateway", "receiver_agent": "monetary_sector", "task": "repo_rate",
                "conversation_id": conv(), "call_chain": ["gateway"]}
        assert http.post("/a2a/v1/requests", json=body).status_code == 403
        assert http.get("/a2a/v1/agents").status_code == 200
