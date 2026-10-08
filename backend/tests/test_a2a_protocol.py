"""Unit and failure tests for the A2A protocol layer (models, registry, routing, guards, errors)."""
from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from a2a_helpers import Runtime, signal_output, source
from core.protocols.a2a.client import A2AClient
from core.protocols.a2a.dependencies import CROSS_SECTOR_DEPENDENCIES, is_allowed
from core.protocols.a2a.exceptions import DataSourceError, ErrorCode
from core.protocols.a2a.executor_adapter import SECTOR_ANALYSIS
from core.protocols.a2a.messages import (
    A2ARequest,
    A2AResponse,
    HandlerOutput,
    IndicatorObservation,
    IndicatorSignal,
    PeerQuery,
    SourceProvenance,
)
from core.protocols.a2a.provenance import provenance_from_artifact, provenance_from_citation
from core.protocols.a2a.router import lexical_route, route_query


def make_request(**overrides) -> A2ARequest:
    base = dict(sender_agent="orchestrator", receiver_agent="monetary_sector", task="repo_rate",
                conversation_id="c1", call_chain=("orchestrator",))
    return A2ARequest(**{**base, **overrides})


# --------------------------------------------------------------------------- models
class TestModels:
    def test_request_defaults_generate_ids(self):
        a, b = make_request(), make_request()
        assert a.request_id != b.request_id and a.parent_request_id is None

    @pytest.mark.parametrize("override", [
        {"sender_agent": ""}, {"task": " "}, {"depth": -1}, {"timeout_seconds": 0},
        {"unexpected": 1}, {"parent_request_id": "same", "request_id": "same"},
    ])
    def test_request_rejects_invalid_fields(self, override):
        with pytest.raises(ValidationError):
            make_request(**override)

    def test_request_is_immutable(self):
        with pytest.raises(ValidationError):
            make_request().task = "other"

    def test_response_status_is_constrained(self):
        with pytest.raises(ValidationError):
            A2AResponse(request_id="r", sender_agent="a", receiver_agent="b", status="maybe")

    def test_signal_requires_observation_and_finite_values(self):
        with pytest.raises(ValidationError):
            IndicatorSignal(owner_agent="x", observations=[])
        with pytest.raises(ValidationError):
            IndicatorObservation(indicator_id="i", label="l", value=float("nan"))

    def test_peer_query_forbids_extra_keys(self):
        with pytest.raises(ValidationError):
            PeerQuery.model_validate({"question": "q", "sql": "drop"})


# --------------------------------------------------------------------------- registry / routing
class TestRegistryAndRouting:
    def setup_method(self):
        self.rt = Runtime()
        self.rt.add_agent("finance_sector", capabilities=["bank_credit_growth", "deposit_growth"],
                          tags=["npa"])
        self.rt.add_agent("fiscal_sector", capabilities=["fiscal_deficit"], keywords=["union budget"])
        for agent in ("finance_sector", "fiscal_sector"):
            self.rt.add_handler(agent, SECTOR_ANALYSIS, self._noop)

    @staticmethod
    async def _noop(request, ctx):
        return signal_output()

    def test_lookup_by_id_and_capability(self):
        reg = self.rt.registry
        assert reg.get_agent("finance_sector").name == "finance_sector card"
        assert reg.get_agent("missing") is None
        assert [c.agent_id for c in reg.find_by_capability("bank_credit_growth")] == ["finance_sector"]
        assert [c.agent_id for c in reg.find_by_capability(SECTOR_ANALYSIS)] == ["finance_sector", "fiscal_sector"]
        assert reg.find_by_capability("nothing") == []
        assert len(reg.list_agents()) == 2

    def test_registered_handler_extends_card_supported_tasks(self):
        assert SECTOR_ANALYSIS in self.rt.registry.get_agent("fiscal_sector").supported_tasks

    def test_handler_for_unknown_agent_is_rejected(self):
        with pytest.raises(Exception, match="not in the registry"):
            self.rt.add_handler("ghost", "x", self._noop)

    def test_routing_uses_card_metadata_only(self):
        ids = [c.agent_id for c in lexical_route("How is bank credit growth and the union budget?", self.rt.registry)]
        assert ids == ["finance_sector", "fiscal_sector"]
        assert [c.agent_id for c in lexical_route("NPA ratios", self.rt.registry)] == ["finance_sector"]

    async def test_unmatched_query_falls_back_to_llm_restricted_to_registered_ids(self):
        async def llm(_prompt: str) -> str:
            return 'Sure: ["fiscal_sector", "made_up_sector", "fiscal_sector"]'

        decision = await route_query("zzz unrelated", self.rt.registry, llm)
        assert decision.method == "llm" and [c.agent_id for c in decision.choices] == ["fiscal_sector"]

    async def test_llm_failure_and_garbage_fall_back_to_defaults(self, monkeypatch):
        from core.config import settings
        monkeypatch.setattr(settings, "A2A_DEFAULT_AGENTS", ["finance_sector", "unregistered"])

        async def boom(_prompt: str) -> str:
            raise RuntimeError("groq down")

        async def garbage(_prompt: str) -> str:
            return "no json here"

        for llm in (boom, garbage, None):
            decision = await route_query("zzz unrelated", self.rt.registry, llm)
            assert decision.method == "default"
            assert [c.agent_id for c in decision.choices] == ["finance_sector"]


# --------------------------------------------------------------------------- dependencies
class TestDependencies:
    def test_orchestrator_unrestricted_sectors_restricted(self):
        assert is_allowed("orchestrator", "anything", "any_task")
        assert is_allowed("external_sector", "monetary_sector", "repo_rate")
        assert not is_allowed("external_sector", "monetary_sector", "sector_analysis")
        assert not is_allowed("monetary_sector", "external_sector", "forex_reserves")

    def test_every_edge_documents_a_rationale_and_no_self_edges(self):
        for dep in CROSS_SECTOR_DEPENDENCIES:
            assert dep.rationale and dep.consumer != dep.provider


# --------------------------------------------------------------------------- server behaviour
class TestServerFailures:
    def setup_method(self):
        self.rt = Runtime(max_depth=3, max_hops=6, timeout=0.2)
        self.rt.add_agent("monetary_sector")
        self.rt.add_agent("external_sector")
        self.client = self.rt.client("orchestrator", max_retries=0)

    async def _call(self, task="repo_rate", receiver="monetary_sector", **kw):
        return await self.client.send_request(receiver, task, {}, conversation_id="c-test", **kw)

    async def test_success_returns_typed_result_and_sources(self):
        async def handler(request, ctx):
            return signal_output()

        self.rt.add_handler("monetary_sector", "repo_rate", handler, params_model=PeerQuery,
                            result_model=IndicatorSignal)
        resp = await self._call()
        assert resp.status == "success" and resp.sender_agent == "monetary_sector"
        assert resp.receiver_agent == "orchestrator" and resp.sources[0].table == "Table 1"

    async def test_agent_not_found(self):
        resp = await self._call(receiver="ghost_sector")
        assert resp.status == "failed" and resp.error_codes == [ErrorCode.AGENT_NOT_FOUND]

    async def test_unsupported_capability(self):
        resp = await self._call(task="forex_reserves")
        assert resp.error_codes == [ErrorCode.UNSUPPORTED_CAPABILITY]

    async def test_advertised_task_without_handler_is_unavailable(self):
        self.rt.registry.get_agent("monetary_sector").supported_tasks.append("repo_rate")
        resp = await self._call()
        assert resp.error_codes == [ErrorCode.AGENT_UNAVAILABLE]

    async def test_invalid_parameters_rejected_before_handler_runs(self):
        called = False

        async def handler(request, ctx):
            nonlocal called
            called = True
            return signal_output()

        self.rt.add_handler("monetary_sector", "repo_rate", handler, params_model=PeerQuery)
        resp = await self.client.send_request("monetary_sector", "repo_rate", {"bad": 1},
                                              conversation_id="c-test")
        assert resp.error_codes == [ErrorCode.INVALID_REQUEST] and not called

    async def test_timeout_returns_structured_error(self):
        async def slow(request, ctx):
            await asyncio.sleep(5)
            return signal_output()

        self.rt.add_handler("monetary_sector", "repo_rate", slow)
        resp = await self._call(timeout=0.05)
        assert resp.error_codes == [ErrorCode.AGENT_TIMEOUT]
        assert "monetary_sector" in resp.errors[0].message

    async def test_mcp_failure_maps_to_data_source_error(self):
        async def failing(request, ctx):
            raise DataSourceError("MCP server returned an error")

        self.rt.add_handler("monetary_sector", "repo_rate", failing)
        resp = await self._call()
        assert resp.status == "failed" and resp.error_codes == [ErrorCode.DATA_SOURCE_ERROR]

    async def test_unexpected_exception_does_not_crash_server(self):
        async def buggy(request, ctx):
            raise ZeroDivisionError("boom")

        self.rt.add_handler("monetary_sector", "repo_rate", buggy)
        resp = await self._call()
        assert resp.error_codes == [ErrorCode.AGENT_ERROR] and "ZeroDivisionError" in resp.errors[0].message

    async def test_result_violating_schema_is_invalid_response(self):
        async def wrong(request, ctx):
            return HandlerOutput(result={"owner_agent": "x"}, sources=[source()])

        self.rt.add_handler("monetary_sector", "repo_rate", wrong, result_model=IndicatorSignal)
        resp = await self._call()
        assert resp.error_codes == [ErrorCode.INVALID_RESPONSE]

    async def test_result_without_sources_is_rejected(self):
        async def unsourced(request, ctx):
            return HandlerOutput(result={"value": 5.25})

        self.rt.add_handler("monetary_sector", "repo_rate", unsourced)
        resp = await self._call()
        assert resp.error_codes == [ErrorCode.INVALID_RESPONSE] and "No Source" in resp.errors[0].message

    async def test_handler_returning_wrong_type_is_invalid_response(self):
        async def wrong_type(request, ctx):
            return {"result": 1}

        self.rt.add_handler("monetary_sector", "repo_rate", wrong_type)
        assert (await self._call()).error_codes == [ErrorCode.INVALID_RESPONSE]

    async def test_undeclared_sector_dependency_is_denied(self):
        async def handler(request, ctx):
            return signal_output()

        self.rt.add_handler("external_sector", "forex_reserves", handler)
        resp = await self.rt.client("monetary_sector").send_request("external_sector", "forex_reserves", {})
        assert resp.error_codes == [ErrorCode.DEPENDENCY_NOT_ALLOWED]


# --------------------------------------------------------------------------- loop protection
class TestLoopProtection:
    def setup_method(self):
        self.rt = Runtime(max_depth=3, max_hops=4, timeout=1.0)
        for agent in ("monetary_sector", "finance_sector", "fiscal_sector"):
            self.rt.add_agent(agent)

        async def ok(request, ctx):
            return signal_output()

        self.ok = ok
        self.rt.add_handler("monetary_sector", "repo_rate", ok)
        self.rt.add_handler("finance_sector", "bank_credit_growth", ok)

    async def test_circular_delegation_detected(self):
        req = make_request(sender_agent="fiscal_sector", receiver_agent="finance_sector",
                           task="bank_credit_growth", depth=2,
                           call_chain=("orchestrator", "finance_sector", "fiscal_sector"))
        resp = await self.rt.server.handle(req)
        assert resp.error_codes == [ErrorCode.CIRCULAR_DELEGATION]

    async def test_self_delegation_detected(self):
        req = make_request(sender_agent="orchestrator", receiver_agent="orchestrator",
                           call_chain=("orchestrator",))
        assert (await self.rt.server.handle(req)).error_codes == [ErrorCode.CIRCULAR_DELEGATION]

    async def test_max_depth_enforced(self):
        req = make_request(depth=4)
        assert (await self.rt.server.handle(req)).error_codes == [ErrorCode.MAX_DEPTH_EXCEEDED]
        assert (await self.rt.server.handle(make_request(depth=3))).status == "success"

    async def test_hop_budget_enforced_per_conversation(self):
        client = self.rt.client("orchestrator", max_retries=0)
        results = [
            await client.send_request("monetary_sector", "repo_rate", {"n": i}, conversation_id="hops")
            for i in range(6)
        ]
        assert [r.status for r in results[:4]] == ["success"] * 4
        assert results[4].error_codes == [ErrorCode.MAX_HOPS_EXCEEDED]
        other = await client.send_request("monetary_sector", "repo_rate", {}, conversation_id="fresh")
        assert other.status == "success"

    async def test_duplicate_request_rejected_but_retry_with_same_id_allowed(self):
        first = make_request(parameters={"q": 1})
        twin = make_request(parameters={"q": 1})
        assert (await self.rt.server.handle(first)).status == "success"
        assert (await self.rt.server.handle(first)).status == "success"
        assert (await self.rt.server.handle(twin)).error_codes == [ErrorCode.DUPLICATE_REQUEST]

    async def test_chain_must_end_with_sender(self):
        req = make_request(call_chain=("orchestrator", "finance_sector"))
        assert (await self.rt.server.handle(req)).error_codes == [ErrorCode.INVALID_REQUEST]


# --------------------------------------------------------------------------- client
class TestClient:
    def _request(self) -> A2ARequest:
        return make_request()

    async def test_retries_only_retryable_errors(self):
        attempts = []

        class Flaky:
            async def send(self, request):
                attempts.append(request.request_id)
                if len(attempts) < 3:
                    raise ConnectionError("down")
                return A2AResponse(request_id=request.request_id, sender_agent="monetary_sector",
                                   receiver_agent="orchestrator", status="success", sources=[source()])

        client = A2AClient("orchestrator", transport=Flaky(), max_retries=2)
        resp = await client.send(self._request())
        assert resp.status == "success" and len(attempts) == 3 and len(set(attempts)) == 1

    async def test_retries_exhausted_returns_last_error(self):
        class Down:
            async def send(self, request):
                raise ConnectionError("down")

        resp = await A2AClient("orchestrator", transport=Down(), max_retries=1).send(self._request())
        assert resp.error_codes == [ErrorCode.TRANSPORT_ERROR] and "ConnectionError" in resp.errors[0].message

    async def test_non_retryable_error_is_not_retried(self):
        calls = []

        class Denied:
            async def send(self, request):
                calls.append(1)
                return A2AResponse(
                    request_id=request.request_id, sender_agent="monetary_sector",
                    receiver_agent="orchestrator", status="failed",
                    errors=[{"code": "UNSUPPORTED_CAPABILITY", "message": "no"}])

        resp = await A2AClient("orchestrator", transport=Denied(), max_retries=3).send(self._request())
        assert resp.error_codes == [ErrorCode.UNSUPPORTED_CAPABILITY] and len(calls) == 1

    async def test_transport_timeout(self):
        class Hang:
            async def send(self, request):
                await asyncio.sleep(10)

        client = A2AClient("orchestrator", transport=Hang(), max_retries=0, default_timeout=0.05)
        req = make_request(timeout_seconds=0.05)
        import core.protocols.a2a.client as client_module
        original = client_module._TRANSPORT_GRACE_SECONDS
        client_module._TRANSPORT_GRACE_SECONDS = 0.05
        try:
            resp = await client.send(req)
        finally:
            client_module._TRANSPORT_GRACE_SECONDS = original
        assert resp.error_codes == [ErrorCode.AGENT_TIMEOUT]

    async def test_malformed_and_mismatched_responses_are_invalid(self):
        class Garbage:
            async def send(self, request):
                return {"nonsense": True}

        class Mismatch:
            async def send(self, request):
                return A2AResponse(request_id="other", sender_agent="monetary_sector",
                                   receiver_agent="orchestrator", status="success", sources=[source()])

        for transport in (Garbage(), Mismatch()):
            resp = await A2AClient("orchestrator", transport=transport, max_retries=0).send(self._request())
            assert resp.error_codes == [ErrorCode.INVALID_RESPONSE]

    async def test_invalid_request_arguments_return_structured_error(self):
        resp = await A2AClient("orchestrator", max_retries=0).send_request("", "task")
        assert resp.status == "failed" and resp.error_codes == [ErrorCode.INVALID_REQUEST]

    async def test_send_many_runs_concurrently(self):
        rt = Runtime(timeout=2.0)
        rt.add_agent("monetary_sector")

        async def slow(request, ctx):
            await asyncio.sleep(0.2)
            return signal_output()

        rt.add_handler("monetary_sector", "repo_rate", slow)
        client = rt.client("orchestrator")
        requests = [client.build_request("monetary_sector", "repo_rate", {"n": i}, conversation_id="par")
                    for i in range(5)]
        loop = asyncio.get_running_loop()
        started = loop.time()
        responses = await client.send_many(requests)
        assert [r.status for r in responses] == ["success"] * 5
        assert loop.time() - started < 0.8

    def test_discover_excludes_self(self):
        rt = Runtime()
        rt.add_agent("finance_sector", capabilities=["credit"])
        rt.add_agent("fiscal_sector", capabilities=["credit"])
        assert [c.agent_id for c in rt.client("finance_sector").discover("credit")] == ["fiscal_sector"]


# --------------------------------------------------------------------------- provenance
class TestProvenance:
    def test_citation_fields_are_mapped_without_invention(self):
        prov = provenance_from_citation(
            {"source_authority": "RBI", "retrieval_url": "https://x", "document_title": "Bulletin",
             "table_reference": "Table 9", "observation_period": "2026-04",
             "fetched_at": "2026-05-01T10:00:00+00:00", "indicator_id": "in.macro.x"}, "fallback")
        assert (prov.source_name, prov.source_url, prov.dataset, prov.table) == ("RBI", "https://x", "Bulletin", "Table 9")
        assert prov.reporting_period == "2026-04" and prov.record_reference == "in.macro.x"
        assert prov.retrieved_at.year == 2026 and prov.page_or_section is None

    def test_artifact_without_citations_gets_artifact_level_reference(self):
        [src] = provenance_from_artifact({"metrics": 1}, "Agent X", "report", "abc123")
        assert (src.source_name, src.dataset, src.record_reference) == ("Agent X", "report", "abc123")

    def test_nested_prices_style_citations_are_collected_and_deduplicated(self):
        obs = {"source_authority": "MoSPI", "dataset_reference": "CPI", "series_code": "S1",
               "observation_period": "2026-03", "indicator_id": "cpi"}
        content = {"citation": {"observations": [obs, dict(obs)]}}
        assert len(provenance_from_artifact(content, "Prices", "n", None)) == 1


# --------------------------------------------------------------------------- trace
class TestTrace:
    async def test_full_request_chain_can_be_reconstructed(self):
        rt = Runtime(timeout=2.0)
        for agent in ("monetary_sector", "finance_sector"):
            rt.add_agent(agent)

        async def monetary(request, ctx):
            return signal_output(src=source("RBI DBIE", "Table 7"))

        async def finance(request, ctx):
            inner = await rt.client("finance_sector").send_request("monetary_sector", "repo_rate", {}, parent=ctx)
            return HandlerOutput(result={"repo": inner.result}, sources=inner.sources)

        rt.add_handler("monetary_sector", "repo_rate", monetary)
        rt.add_handler("finance_sector", "bank_credit_growth", finance)

        resp = await rt.client("orchestrator").send_request(
            "finance_sector", "bank_credit_growth", {}, conversation_id="C123")

        assert resp.status == "success"
        # Provenance survives two A2A hops unchanged.
        assert resp.sources[0].table == "Table 7" and resp.sources[0].record_reference == "row-7"

        nodes = rt.trace.get_trace("C123")
        by_receiver = {n["receiver_agent"]: n for n in nodes}
        assert by_receiver["finance_sector"]["parent_request_id"] is None
        assert by_receiver["monetary_sector"]["parent_request_id"] == by_receiver["finance_sector"]["request_id"]
        assert [n["depth"] for n in nodes] == [0, 1]
        [root] = rt.trace.get_tree("C123")
        assert root["receiver_agent"] == "finance_sector"
        assert root["children"][0]["receiver_agent"] == "monetary_sector"
        assert all(n["status"] == "success" for n in nodes)

    def test_old_conversations_are_evicted(self):
        from core.protocols.a2a.trace import TraceStore
        store = TraceStore(max_conversations=2)
        for cid in ("a", "b", "c"):
            store.begin(make_request(conversation_id=cid))
        assert store.get_trace("a") == [] and store.get_trace("c")


def test_source_provenance_requires_a_name():
    with pytest.raises(ValidationError):
        SourceProvenance(source_name="")


def test_executor_events_accept_datetime_timestamps():
    """Sector executors pass datetime objects; the models must store ISO strings, not reject them."""
    from datetime import datetime, timezone

    from core.protocols.a2a.models import A2AMessage, TaskState, TaskStatusUpdateEvent

    now = datetime.now(timezone.utc)
    event = TaskStatusUpdateEvent(task_id="t", status=TaskState.WORKING, timestamp=now)
    assert event.timestamp == now.isoformat()
    assert A2AMessage(role="agent", timestamp=now).timestamp == now.isoformat()
