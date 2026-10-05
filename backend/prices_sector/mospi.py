"""Metadata-led MoSPI adapter, used only by the canonical Prices client."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from .metadata import choose_base, find_code, label_key, metadata_values, number, observation_period, shift_month
from .models import PriceObservation, PriceRequest, PricesIntent
from .normalization import normalize_mcp_response

MOSPI_URL = 'https://mcp.mospi.gov.in/'
Call = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

# Exact official labels resolve metadata codes, never substring matches on rows.
CPI_LABELS = {
    'headline': ['CPI (General)', 'General index', 'General'],
    'food': ['Food', 'Food and beverages'],
    'cfpi': ['Consumer Food Price Index', 'Consumer food price', 'CFPI'],
    'fuel': ['Fuel and light'],
    'housing': ['Housing'],
    'health': ['Health'],
    'transport': ['Transport and communication', 'Transport'],
    'core': ['Core CPI', 'Core consumer price index', 'CPI excluding food and fuel'],
}
WPI_LABELS = {
    'headline': ['Wholesale price index', 'All commodities'],
    'primary': ['Primary articles'], 'fuel': ['Fuel and power'],
    'manufactured': ['Manufactured products'], 'food': ['Food index'],
}
ROW_DIMENSIONS = {'major_group': 'majorgroup', 'sub_group': 'subgroup', 'subgroup': 'subgroup'}


async def discover(call: Call, dataset: str, base_year: str | None) -> tuple[str, dict[str, Any]]:
    indicators = normalize_mcp_response(await call('get_indicators', {'dataset': dataset}))
    if indicators.get('error'):
        raise ValueError(indicators['error'])
    base = choose_base(indicators, dataset, base_year)
    args = {'dataset': dataset, 'base_year': base}
    if dataset == 'CPI':
        args.update(level='Group', series='Current')
    payload = normalize_mcp_response(await call('get_metadata', args))
    if payload.get('error'):
        raise ValueError(payload['error'])
    meta = metadata_values(payload)
    if not meta:
        raise ValueError(f'No usable {dataset} metadata')
    return base, meta


def resolve_category(meta: dict[str, Any], request: PriceRequest) -> tuple[str, str, str]:
    labels = (CPI_LABELS if request.indicator == 'cpi' else WPI_LABELS).get(request.category, [request.category])
    dimensions = ('division', 'group', 'subgroup') if request.indicator == 'cpi' else ('major_group',)
    for label in labels:
        for dimension in dimensions:
            try:
                code, name = find_code(meta, dimension, [label])
                return dimension, code, name
            except ValueError:
                continue
    raise ValueError(f'{request.category}: requested category is not exposed by this series metadata')


def matches_row(row: dict[str, Any], dimension: str, code: str, name: str) -> bool:
    key = ROW_DIMENSIONS.get(dimension, dimension)
    row_code = row.get(f'{dimension}_code')
    if row_code is not None:
        if str(row_code) != code:
            return False
    elif label_key(row.get(key, row.get(f'{dimension}_name'))) != label_key(name):
        return False
    # A parent filter also returns its children. Only accept the aggregate itself.
    hierarchy = ['major_group', 'division', 'group', 'subgroup', 'sub_group', 'class', 'sub_class', 'sub_subgroup', 'item']
    for child in hierarchy[hierarchy.index(dimension) + 1:]:
        if child in ('subgroup', 'sub_group') and dimension in ('subgroup', 'sub_group'):
            continue
        field = ROW_DIMENSIONS.get(child, child)
        if row.get(field) not in (None, '', 'NA', 'N/A') or row.get(f'{child}_code') not in (None, ''):
            return False
    return True


async def fetch_pages(call: Call, dataset: str, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    for page in range(1, 101):
        try:
            payload = normalize_mcp_response(await call('get_data', {'dataset': dataset, 'filters': {**filters, 'limit': 30, 'page': page}}))
            if payload.get('error'):
                raise ValueError(payload['error'])
            batch = payload.get('data', [])
            if not isinstance(batch, list):
                raise ValueError('Source returned no observation list')
            if not batch:
                return rows, []
            fingerprint = json.dumps(batch, sort_keys=True, default=str)
            if fingerprint in fingerprints:
                return rows, ['Source repeated a page; historical coverage is incomplete']
            fingerprints.add(fingerprint)
            rows.extend(r for r in batch if isinstance(r, dict))
            pagination = payload.get('meta_data', {})
            total = pagination.get('totalPages') if isinstance(pagination, dict) else None
            if total is not None and page >= int(total):
                return rows, []
            if total is None and len(batch) < 30:
                return rows, []
        except Exception as exc:
            # Isolate a failed page and retain verified records from earlier pages.
            return rows, [f'{dataset} page {page}: {type(exc).__name__}: {exc}']
    return rows, ['Source pagination exceeded 100 pages; historical coverage is incomplete']


async def fetch_request(call: Call, intent: PricesIntent, request: PriceRequest,
                        base: str, meta: dict[str, Any], start: str, end: str
                        ) -> tuple[list[PriceObservation], list[str], dict[str, Any]]:
    dataset = request.indicator.upper()
    dimension, code, name = resolve_category(meta, request)
    filters: dict[str, Any] = {'base_year': base, f'{dimension}_code': code}
    sector_name = ''
    if dataset == 'CPI':
        state_code, state_name = find_code(meta, 'state', ['All India'] if intent.geography.casefold() == 'india' else [intent.geography])
        sector_code, sector_name = find_code(meta, 'sector', [request.sector])
        filters.update(series='Current', state_code=state_code, sector_code=sector_code)
    # WPI needs matching prior-year indices for YoY, never different bases.
    fetch_start = shift_month(start, -12) if dataset == 'WPI' else start
    years = list(range(int(fetch_start[:4]), int(end[:4]) + 1))
    available_years = {str(y.get('year')) for y in meta.get('year', []) if isinstance(y, dict)}
    if available_years:
        years = [y for y in years if str(y) in available_years]
    if not years:
        raise ValueError(f'{dataset} base {base} has no coverage in the requested period')
    filters['year'] = ','.join(map(str, years))
    rows, errors = await fetch_pages(call, dataset, filters)
    selected: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    for row in rows:
        if str(row.get('base_year', base)) != base or not matches_row(row, dimension, code, name):
            continue
        if dataset == 'CPI':
            if row.get('series') not in (None, 'Current'):
                continue
            if row.get('sector') is not None and label_key(row['sector']) != label_key(sector_name):
                continue
            if row.get('state') is not None and label_key(row['state']) != label_key(state_name):
                continue
            if row.get('sector_code') is not None and str(row['sector_code']) != sector_code:
                continue
            if row.get('state_code') is not None and str(row['state_code']) != state_code:
                continue
        period = observation_period(row)
        if period is None:
            errors.append('Rejected observation with missing or invalid actual period')
            continue
        if not fetch_start <= period <= end:
            continue
        if period in selected and any(row.get(k) != selected[period].get(k) for k in ('inflation', 'index', 'index_value')):
            conflicts.add(period)
        selected[period] = row
    for period in conflicts:
        selected.pop(period, None)
        errors.append(f'Conflicting observations for {period}; value omitted')
    observations = []
    for period, row in sorted(selected.items()):
        if period < start:
            continue
        metadata: dict[str, Any] = {'sector': request.sector, 'category': request.category, 'series': row.get('series'), 'geography': intent.geography}
        value = number(row.get('inflation'))
        if dataset == 'WPI' and value is None:
            previous_period = shift_month(period, -12)
            previous = selected.get(previous_period, {})
            current_index, previous_index = number(row.get('index_value')), number(previous.get('index_value'))
            if current_index is not None and previous_index is not None and previous_index > 0:
                value = (current_index / previous_index - 1) * 100
                metadata.update(calculation='100 * (index / previous_year_index - 1)', index=current_index,
                                previous_year_index=previous_index, previous_year_period=previous_period)
        if value is None:
            continue
        series_code = f'{dataset}:{base}:{dimension}={code}'
        if dataset == 'CPI':
            series_code += f':state={state_code}:sector={sector_code}:Current'
        observations.append(PriceObservation(
            source_authority='National Statistical Office (NSO), MoSPI' if dataset == 'CPI' else 'Office of Economic Adviser / MoSPI',
            dataset_reference=dataset, indicator_id=f'in.macro.prices.{request.indicator}_{request.category}_{request.sector}_yoy',
            indicator=f'{name} ({sector_name})' if sector_name else name, series_code=series_code, request_id=request.key,
            observation_period=period, base_year=base, value=value, unit='% YoY', url=MOSPI_URL,
            mcp_server=MOSPI_URL, mcp_tool='get_data', retrieved_at=datetime.now(timezone.utc), metadata=metadata))
    return observations, list(dict.fromkeys(errors)), {'dataset': dataset, 'base_year': base, 'filters': filters,
        'period_range_requested': [start, end], 'index_period_range_requested': [fetch_start, end]}
