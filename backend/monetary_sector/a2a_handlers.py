"""A2A capabilities the Monetary sector exposes to peer agents."""
from __future__ import annotations

from core.protocols.a2a import a2a_server
from core.protocols.a2a.exceptions import DataSourceError
from core.protocols.a2a.messages import (
    A2ACallContext, A2ARequest, HandlerOutput, IndicatorObservation, IndicatorSignal, PeerQuery,
)
from core.protocols.a2a.provenance import provenance_from_citation
from core.protocols.a2a.signals import signal_output
from monetary_sector import client

AGENT_ID = "monetary_sector"


async def repo_rate(request: A2ARequest, ctx: A2ACallContext) -> HandlerOutput:
    """Latest RBI policy repo rate with its DBIE citation."""
    try:
        records = await client.fetch_policy_rates(lookback_months=3)
    except Exception as exc:
        raise DataSourceError(f"Policy rate retrieval failed: {type(exc).__name__}: {exc}") from exc
    with_rate = [r for r in records if r.repo_rate_pct is not None]
    if not with_rate:
        raise DataSourceError("No policy repo rate observation is available from the Monetary sector sources.")
    latest = max(with_rate, key=lambda r: r.period)
    obs = IndicatorObservation(
        indicator_id="in.macro.monetary.repo_rate", label="RBI policy repo rate",
        value=latest.repo_rate_pct, unit="%", observation_period=latest.period,
        data_status=latest.citation.freshness.value,
    )
    return signal_output(AGENT_ID, [obs], [provenance_from_citation(latest.citation, "RBI DBIE")])


def register() -> None:
    a2a_server.register_handler(
        AGENT_ID, "repo_rate", repo_rate, params_model=PeerQuery, result_model=IndicatorSignal,
        description="Latest RBI policy repo rate.",
    )
