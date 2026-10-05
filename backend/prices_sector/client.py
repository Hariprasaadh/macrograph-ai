"""Single Prices source router and retrieval pipeline."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from fastmcp import Client
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from . import mospi
from .metadata import number, observation_period, shift_month
from .models import PriceObservation, PriceRequest, PricesIntent, PricesResult
from .normalization import normalize_mcp_response

MOSPI_URL = mospi.MOSPI_URL
IMF_URL = 'https://imf.caseyjhand.com/mcp'
# Verified IMF CPI DSD: COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY.
IMF_CPI_KEY = 'IND.CPI._T.YOY_PCH_PA_PT.M'


async def _imf_request(call, intent: PricesIntent, request: PriceRequest, start: str, end: str):
    if request.indicator != 'cpi' or request.category != 'headline' or request.sector != 'combined' or intent.base_year:
        raise ValueError('IMF retrieval supports monthly headline CPI YoY only; this requested series is unavailable')
    country_code = 'IND'
    if intent.geography.casefold() != 'india':
        metadata = normalize_mcp_response(await call('imf_get_database', {
            'dataflow_id': 'CPI', 'dimension_id': 'COUNTRY', 'codelist_filter': intent.geography}))
        if metadata.get('error'):
            raise ValueError(metadata['error'])
        expected = 'COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY'
        if metadata.get('key_format') != expected:
            raise ValueError('IMF CPI dimension order could not be verified')
        matches = [entry for dimension in metadata.get('dimensions', [])
                   if isinstance(dimension, dict) and dimension.get('id') == 'COUNTRY'
                   for entry in dimension.get('codelist', []) if isinstance(entry, dict)
                   and str(entry.get('name', '')).split(',')[0].strip().casefold() == intent.geography.casefold()]
        if len(matches) != 1 or not matches[0].get('id'):
            raise ValueError(f'IMF country metadata did not uniquely identify {intent.geography}')
        country_code = str(matches[0]['id'])
    # CPI / All Items / YoY percent change / Monthly verified against IMF CPI metadata.
    series_key = f'{country_code}.CPI._T.YOY_PCH_PA_PT.M'
    args = {'dataflow_id': 'CPI', 'key': series_key, 'start_period': start, 'end_period': end,
            'last_n_observations': intent.lookback_months if not intent.start_period else 120}
    if intent.operation in ('latest', 'comparison') and not intent.start_period:
        args.pop('start_period')
    payload = normalize_mcp_response(await call('imf_query_dataset', args))
    if payload.get('error'):
        raise ValueError(payload['error'])
    if payload.get('staged') or payload.get('truncated'):
        raise ValueError('IMF did not return a complete inline observation set')
    rows = payload.get('observations', payload.get('data', []))
    if not isinstance(rows, list):
        raise ValueError('IMF returned no observation list')
    observations, errors = [], []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get('series_key', series_key) != series_key:
            continue
        period, value = observation_period(row), number(row.get('value'))
        if not period or value is None:
            errors.append('IMF returned an invalid period or non-numeric observation')
            continue
        if period > end or (not (intent.operation in ('latest', 'comparison') and not intent.start_period) and period < start):
            continue
        observations.append(PriceObservation(
            source_authority='International Monetary Fund', dataset_reference='CPI',
            indicator_id=f'{country_code.lower()}.macro.prices.cpi_headline_combined_yoy', indicator='Consumer price index (CPI), All Items',
            series_code=series_key, request_id=request.key, observation_period=period, country=intent.geography,
            value=value, unit='% YoY', url='https://data.imf.org/', mcp_server=IMF_URL,
            mcp_tool='imf_query_dataset', retrieved_at=datetime.now(timezone.utc),
            metadata={'country': country_code, 'transformation': 'YOY_PCH_PA_PT', 'status': row.get('status'),
                      'series_attributes': payload.get('series_attributes', {})}))
    if not observations:
        errors.append(f'{intent.geography} CPI unavailable from IMF for the requested period. IMF did not return a valid {intent.geography} CPI observation')
    return observations, errors, {'dataset': 'CPI', 'period_range_requested': [args.get('start_period'), end], 'arguments': args}


async def retrieve_prices(intent: PricesIntent) -> PricesResult:
    """Select one source, discover once per dataset, and isolate each request failure."""
    if intent.operation == 'comparison' and len(intent.countries) > 1:
        return await _retrieve_comparison(intent)
    if intent.geography.casefold() == 'china':
        intent = intent.model_copy(update={'source': 'imf'})
    source = 'IMF' if intent.source == 'imf' else 'MoSPI'
    now = datetime.now(timezone.utc).strftime('%Y-%m')
    end = min(intent.end_period or now, now)
    start = intent.start_period or shift_month(end, -(intent.lookback_months + 3))
    diagnostics: dict[str, Any] = {'intent': intent.model_dump(), 'selected_source': source,
        'mcp': IMF_URL if intent.source == 'imf' else MOSPI_URL,
        'period_range_requested': [start, end], 'calls': [], 'requests': []}
    errors = [{'request': 'intent', 'reason': reason} for reason in intent.errors]
    observations: list[PriceObservation] = []
    requests = list({r.key: r for r in intent.requests}.values())
    if start > end:
        errors.append({'request': 'intent', 'reason': 'Requested period range is in the future or reversed'})
    if not errors:
        try:
            async with Client(diagnostics['mcp'], timeout=45) as session:
                @retry(retry=retry_if_exception_type((httpx.TransportError, TimeoutError)),
                       stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, max=2), reraise=True)
                async def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
                    diagnostics['calls'].append({'tool': name, 'arguments': arguments})
                    return normalize_mcp_response(await session.call_tool(name, arguments))

                metadata: dict[str, Any] = {}
                if intent.source == 'mospi':
                    for dataset in dict.fromkeys(r.indicator.upper() for r in requests):
                        try:
                            metadata[dataset] = await mospi.discover(call, dataset, intent.base_year)
                        except Exception as exc:
                            metadata[dataset] = exc
                semaphore = asyncio.Semaphore(3)

                async def one(request: PriceRequest):
                    async with semaphore:
                        try:
                            if intent.source == 'imf':
                                return await _imf_request(call, intent, request, start, end)
                            discovered = metadata[request.indicator.upper()]
                            if isinstance(discovered, Exception):
                                raise discovered
                            return await mospi.fetch_request(call, intent, request, *discovered, start, end)
                        except Exception as exc:
                            return [], [f'{type(exc).__name__}: {exc}'], {'dataset': request.indicator.upper()}

                for request, (records, issues, detail) in zip(requests, await asyncio.gather(*(one(r) for r in requests))):
                    records.sort(key=lambda r: r.observation_period)
                    if intent.operation == 'latest':
                        records = records[-1:]
                    elif not intent.start_period:
                        records = records[-intent.lookback_months:]
                    if not records and not issues:
                        issues.append('Source returned no usable observations for the requested series and period')
                    if records:
                        latest = records[-1].observation_period
                        stale = not intent.end_period and latest < shift_month(now, -3)
                        for record in records:
                            record.metadata['freshness'] = 'stale' if stale else 'recent'
                            record.metadata['coverage_complete'] = not bool(issues)
                        if stale:
                            issues.append(f'Latest returned period is {latest}; current-period data is unavailable')
                        if intent.operation == 'trend' and not intent.start_period and len(records) < intent.lookback_months:
                            issues.append(f'Only {len(records)} of {intent.lookback_months} requested monthly observations are available in this series')
                    observations.extend(records)
                    errors.extend({'request': request.key, 'reason': issue} for issue in issues)
                    diagnostics['requests'].append({'request': request.key, **detail,
                        'latest_period_returned': records[-1].observation_period if records else None,
                        'number_of_observations': len(records), 'errors': issues})
        except Exception as exc:
            errors.append({'request': 'connection', 'reason': f'{source} MCP connection failed: {type(exc).__name__}: {exc}'})
    available = {o.request_id for o in observations}
    missing = [r.key for r in requests if r.key not in available]
    status = 'partial' if observations and errors else 'available' if observations else 'unavailable'
    diagnostics.update(latest_period_returned=max((o.observation_period for o in observations), default=None),
                       number_of_observations=len(observations), errors=errors, final_status=status)
    return PricesResult(status=status, source=source, observations=observations, missing=missing, errors=errors,
                        error='; '.join(e['reason'] for e in errors) if errors else None, diagnostics=diagnostics)


async def _retrieve_comparison(intent: PricesIntent) -> PricesResult:
    """Use a small common-period window through the existing country adapters."""
    countries = list(dict.fromkeys(intent.countries))
    if len(intent.requests) != 1 or intent.requests[0] != PriceRequest():
        return PricesResult(status='unavailable', error='Country comparisons currently support headline CPI YoY only.')
    async def country_result(country: str) -> PricesResult:
        source = 'imf' if intent.source == 'imf' or country != 'India' else 'mospi'
        # Comparison keeps up to three recent records for alignment, without a broad history scan.
        return await retrieve_prices(intent.model_copy(update={
            'countries': [], 'geography': country, 'source': source, 'lookback_months': 3}))
    results = await asyncio.gather(*(country_result(c) for c in countries))
    by_country = {c: {o.observation_period: o for o in r.observations if o.unit == '% YoY'}
                  for c, r in zip(countries, results)}
    common = set.intersection(*(set(records) for records in by_country.values()))
    aligned_period = max(common) if common else None
    observations, errors, missing = [], [], []
    for country, result in zip(countries, results):
        errors.extend({'request': f'{country}:{e["request"]}', 'reason': e['reason']} for e in result.errors)
        records = by_country[country]
        if not records:
            missing.append(country)
            reason = f'{country} CPI unavailable from {result.source} for the requested period.'
            if result.source == 'IMF':
                reason += f' IMF did not return a valid {country} CPI observation.'
            errors.append({'request': country, 'reason': reason})
            continue
        observation = records[aligned_period or max(records)].model_copy(deep=True)
        observation.country = country
        observation.request_id = f'{country}:{observation.request_id}'
        observation.metadata.update(country=country, latest_available_period=max(records),
                                    comparison_period=aligned_period)
        observations.append(observation)
    if not aligned_period and not missing:
        errors.append({'request': 'comparison', 'reason':
            'No common monthly period in the bounded window; actual latest periods are shown and differ.'})
    status = 'partial' if observations and (errors or missing) else 'available' if observations else 'unavailable'
    sources = list(dict.fromkeys(r.source for r in results if r.source))
    return PricesResult(status=status, source=' / '.join(sources), observations=observations,
        missing=missing, errors=errors, error='; '.join(e['reason'] for e in errors) or None,
        diagnostics={'intent': intent.model_dump(), 'aligned_period': aligned_period,
                     'comparison_complete': len(observations) == len(countries) and not errors,
                     'countries': {c: r.diagnostics for c, r in zip(countries, results)}, 'final_status': status})


async def fetch_cpi_inflation(lookback_months: int = 12, geography: str = 'India', category: str | None = None) -> PricesResult:
    return await retrieve_prices(PricesIntent(operation='trend', lookback_months=lookback_months,
        geography=geography, requests=[PriceRequest(category=category or 'headline')]))


async def fetch_cpi_subgroups(lookback_months: int = 12, categories: list[str] | None = None) -> PricesResult:
    return await retrieve_prices(PricesIntent(operation='trend', lookback_months=lookback_months,
        requests=[PriceRequest(category=c) for c in categories or ['food', 'fuel', 'housing', 'health', 'transport']]))


async def fetch_wpi_inflation(lookback_months: int = 12, category: str | None = None) -> PricesResult:
    return await retrieve_prices(PricesIntent(operation='trend', lookback_months=lookback_months,
        requests=[PriceRequest(indicator='wpi', category=category or 'headline')]))
