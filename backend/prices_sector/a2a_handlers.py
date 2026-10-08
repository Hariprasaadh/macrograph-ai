"""A2A capabilities the Prices sector exposes to peer agents."""
from __future__ import annotations

from core.protocols.a2a import a2a_server
from core.protocols.a2a.exceptions import DataSourceError
from core.protocols.a2a.messages import (
    A2ACallContext, A2ARequest, HandlerOutput, IndicatorObservation, IndicatorSignal, PeerQuery,
)
from core.protocols.a2a.provenance import provenance_from_citation
from core.protocols.a2a.signals import signal_output
from prices_sector.agent import prices_agent_node

AGENT_ID = "prices_sector"
_HEADLINE_QUERY = "latest India headline CPI inflation"


async def cpi_headline(request: A2ARequest, ctx: A2ACallContext) -> HandlerOutput:
    """Latest all-India headline CPI inflation, retrieved through the Prices MCP server."""
    result = await prices_agent_node({"query": _HEADLINE_QUERY})
    observations = result["prices_sector_data"].get("observations", [])
    if not observations:
        reasons = "; ".join(result.get("prices_sector_errors", [])) or "no observation returned"
        raise DataSourceError(f"Headline CPI unavailable from the Prices MCP: {reasons}")
    latest = observations[0]
    obs = IndicatorObservation(
        indicator_id="in.macro.prices.cpi_headline", label="Headline CPI inflation (YoY)",
        value=latest["value"], unit=latest["unit"], observation_period=latest["observation_period"],
        data_status=latest["retrieval_status"],
    )
    return signal_output(AGENT_ID, [obs], [provenance_from_citation(latest, "MoSPI")])


def register() -> None:
    a2a_server.register_handler(
        AGENT_ID, "cpi_headline", cpi_headline, params_model=PeerQuery, result_model=IndicatorSignal,
        description="Latest all-India headline CPI inflation.",
    )
