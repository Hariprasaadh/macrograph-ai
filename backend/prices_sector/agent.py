"""Factual Prices responses via domain MCP, without LLM or graph synthesis."""
from __future__ import annotations

import logging
from typing import Any
from fastmcp import Client

from .intent import is_direct_prices_query, parse_prices_intent
from .mcp_server import mcp_server
from .models import PricesIntent, PricesResult
from .normalization import normalize_mcp_response

logger = logging.getLogger(__name__)


def format_prices_result(intent: PricesIntent, result: PricesResult) -> str:
    if not result.observations:
        return f'Data unavailable. Source: {result.source}.\n\n' + (result.error or 'No usable observation was returned.')
    observations = result.observations
    series = {o.series_code: o for o in observations}
    lines = [f'{intent.geography} price inflation — {result.source}', '']
    if intent.operation == 'comparison':
        lines = ['CPI inflation comparison' if result.status == 'available' else 'CPI inflation comparison - incomplete', '']
        lines += ['| Country | CPI Inflation (% YoY) | Period | Source |', '|---|---:|---|---|']
        for country in intent.countries:
            obs = next((o for o in observations if o.country == country), None)
            if obs is not None:
                source = 'IMF' if obs.mcp_tool == 'imf_query_dataset' else 'MoSPI'
                lines.append(f'| {country} | {obs.value:.2f} | {obs.observation_period} | {source} |')
            else:
                source = 'IMF' if intent.source == 'imf' or country != 'India' else 'MoSPI'
                lines.append(f'| {country} | Unavailable | Unavailable | {source} |')
        aligned = result.diagnostics.get('aligned_period')
        lines += ['', f'Latest common period in the retrieved window: {aligned}.' if aligned else 'No aligned two-country comparison is available.']
    elif intent.operation == 'trend':
        codes = list(series)
        lines += ['| Period | ' + ' | '.join(f'{series[c].dataset_reference}: {series[c].indicator} (% YoY)' for c in codes) + ' |',
                  '|---|' + '---:|' * len(codes)]
        values = {(o.observation_period, o.series_code): o.value for o in observations}
        for period in sorted({o.observation_period for o in observations}):
            cells = [f'{values[period, c]:.2f}' if (period, c) in values else 'Unavailable' for c in codes]
            lines.append(f'| {period} | ' + ' | '.join(cells) + ' |')
    else:
        lines += ['| Indicator | Value | Unit | Period |', '|---|---:|---|---|']
        lines += [f'| {o.indicator} | {o.value:.2f} | {o.unit} | {o.observation_period} |' for o in observations]
        lines += ['', 'Periods shown are the latest returned for each series; retrieval time does not imply current-period coverage.']
    lines += ['', 'Provenance:']
    for obs in series.values():
        lines.append(f'- {obs.country}: {obs.indicator}: {obs.source_authority}; dataset {obs.dataset_reference}; series `{obs.series_code}`; '
                     f'base {obs.base_year or "source-defined"}; MCP {obs.mcp_server} → {obs.mcp_tool}; retrieved {obs.retrieved_at.isoformat()}.')
        if obs.metadata.get('calculation'):
            lines.append('  YoY calculated from published indices of the same series and calendar month one year apart.')
    if result.errors:
        lines += ['', 'Unavailable or incomplete data:']
        lines += [f'- {e["request"]}: {e["reason"]}' for e in result.errors]
    return '\n'.join(lines)


async def prices_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    intent = parse_prices_intent(str(state.get('query', '')))
    arguments = {'source': intent.source, 'operation': intent.operation, 'lookback_months': intent.lookback_months,
                 'requests': [r.model_dump() for r in intent.requests],
                 'filters': intent.model_dump(exclude={'source', 'operation', 'lookback_months', 'requests'})}
    try:
        async with Client(mcp_server) as client:
            payload = normalize_mcp_response(await client.call_tool('get_price_data', arguments))
        result = PricesResult.model_validate(payload)
    except Exception as exc:
        reason = f'Prices MCP request failed: {type(exc).__name__}: {exc}'
        result = PricesResult(status='unavailable', source='IMF' if intent.source == 'imf' else 'MoSPI',
                              error=reason, errors=[{'request': 'prices_mcp', 'reason': reason}])
    logger.info('Prices retrieval: %s', result.diagnostics)
    observations = [o.model_dump(mode='json') for o in result.observations]
    return {'prices_sector_analysis': format_prices_result(intent, result),
            'prices_sector_data': result.model_dump(mode='json'),
            'prices_sector_citations': observations,
            'prices_sector_errors': [f'{e["request"]}: {e["reason"]}' for e in result.errors],
            'prices_sector_freshness': {o.series_code: o.metadata.get('freshness', 'unknown') for o in result.observations},
            'prices_sector_status': 'completed' if result.status == 'available' else result.status}
