"""A2A capabilities the Finance sector exposes to peer agents."""
from __future__ import annotations

from core.protocols.a2a import a2a_server
from core.protocols.a2a.exceptions import DataSourceError
from core.protocols.a2a.messages import (
    A2ACallContext, A2ARequest, HandlerOutput, IndicatorObservation, IndicatorSignal, PeerQuery,
)
from core.protocols.a2a.provenance import provenance_from_citation
from core.protocols.a2a.signals import signal_output
from finance_sector import client

AGENT_ID = "finance_sector"


async def bank_credit_growth(request: A2ARequest, ctx: A2ACallContext) -> HandlerOutput:
    """Latest non-food bank credit growth (YoY) with its RBI citation."""
    try:
        records = await client.fetch_bank_credit_growth(lookback_months=3)
    except Exception as exc:
        raise DataSourceError(f"Bank credit retrieval failed: {type(exc).__name__}: {exc}") from exc
    with_growth = [r for r in records if r.non_food_credit_yoy_pct is not None]
    if not with_growth:
        raise DataSourceError("No non-food credit growth observation is available from the Finance sector sources.")
    latest = max(with_growth, key=lambda r: r.period)
    obs = IndicatorObservation(
        indicator_id="in.macro.monetary.bank_credit_growth", label="Non-food bank credit growth (YoY)",
        value=latest.non_food_credit_yoy_pct, unit="%", observation_period=latest.period,
        data_status=latest.citation.freshness.value,
    )
    return signal_output(AGENT_ID, [obs], [provenance_from_citation(latest.citation, "RBI DBIE")])


def register() -> None:
    a2a_server.register_handler(
        AGENT_ID, "bank_credit_growth", bank_credit_growth, params_model=PeerQuery,
        result_model=IndicatorSignal, description="Latest non-food bank credit growth (YoY).",
    )
