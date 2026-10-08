"""Regression tests from the code review: error scrubbing, no invented provenance, CORS, canonical ids."""
from __future__ import annotations

import logging

from core.orchestrator.a2a_dispatch import aggregate
from core.protocols.a2a.exceptions import ErrorCode
from core.protocols.a2a.messages import A2AErrorInfo, A2AResponse, scrub_error_text, SourceProvenance
from tests.a2a_helpers import Runtime


def test_scrub_redacts_url_query_strings_and_bounds_length():
    text = "GET https://api.example.com/v1/data?api_key=SECRET123&x=1 failed"
    cleaned = scrub_error_text(text)
    assert "SECRET123" not in cleaned and "https://api.example.com/v1/data?<redacted>" in cleaned
    assert len(scrub_error_text("x" * 5000)) <= 303


def test_error_info_scrubs_at_construction():
    info = A2AErrorInfo(code=ErrorCode.DATA_SOURCE_ERROR, message="fail https://h.test/p?token=abc")
    assert "abc" not in info.message


class TestUnexpectedErrors:
    def setup_method(self):
        self.rt = Runtime(timeout=0.5)
        self.rt.add_agent("monetary_sector")
        self.client = self.rt.client("orchestrator", max_retries=0)

    async def test_raw_exception_text_is_not_returned_but_is_logged(self, caplog):
        async def buggy(request, ctx):
            raise RuntimeError("connect to https://x.test/a?key=TOPSECRET refused")

        self.rt.add_handler("monetary_sector", "repo_rate", buggy)
        with caplog.at_level(logging.ERROR, logger="macrograph.a2a"):
            resp = await self.client.send_request("monetary_sector", "repo_rate", {}, conversation_id="c-1")
        assert resp.error_codes == [ErrorCode.AGENT_ERROR]
        assert "TOPSECRET" not in resp.errors[0].message and "RuntimeError" in resp.errors[0].message
        assert any("unhandled error" in r.message and r.exc_info for r in caplog.records)


def test_aggregate_does_not_invent_provenance_or_period():
    src = SourceProvenance(source_name="MoSPI")
    artifact = {
        "type": "json", "name": "a",
        "content": {"block": {"indicators": {"repo_rate": {"latest_value": 5.25}}}},
    }
    response = A2AResponse(
        request_id="r", sender_agent="monetary_sector", receiver_agent="orchestrator", status="success",
        result={"artifacts": [artifact]}, sources=[src],
    )
    merged = aggregate([response])
    obs = merged["collected_observations"][0]
    assert obs["observation_period"] == "unspecified" and obs["data_status"] == "unspecified"
    cite = merged["citations"][0]
    assert cite["provenance_hash"] is None
    assert merged["agent_analyses"][0]["provenance_hash"] is None


def test_canonical_ids_have_one_definition():
    from core.orchestrator import a2a_dispatch
    from core.orchestrator.canonical_ids import CANONICAL_ID_MAP
    assert a2a_dispatch.CANONICAL_ID_MAP is CANONICAL_ID_MAP
    assert CANONICAL_ID_MAP["repo_rate"] == "in.macro.monetary.repo_rate"


def test_cors_is_not_wildcard_with_credentials():
    import main
    cors = next(m for m in main.app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert "*" not in cors.kwargs["allow_origins"] and cors.kwargs["allow_credentials"] is False
