"""Metadata and period utilities for the canonical Prices client."""
from __future__ import annotations

import calendar
import math
import re
from typing import Any


def label_key(value: Any) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', str(value or '').casefold().replace('&', 'and')).strip()


def metadata_values(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get('filter_values', payload.get('data', payload))
    if isinstance(data, list):
        merged: dict[str, Any] = {}
        for part in data:
            if isinstance(part, dict):
                merged.update(part)
        return merged
    return data if isinstance(data, dict) else {}


def choose_base(payload: dict[str, Any], dataset: str, requested: str | None) -> str:
    data = payload.get('data', {})
    entries = data.get('base_year', []) if isinstance(data, dict) else data
    supported = {str(x.get('base_year', x.get('label'))) for x in entries if isinstance(x, dict)} if isinstance(entries, list) else set()
    if requested:
        if requested not in supported:
            raise ValueError(f'{dataset} base year {requested} is not supported by source metadata')
        return requested
    current = payload.get('current_base_year')
    if not current:
        note = str(payload.get('_note', '')) + ' ' + str(payload.get('base_year_coverage', ''))
        match = re.search(r'(?:Latest|Current)\s+base_year\s*(?:is\s*|=\s*)[\'"]([^\'"]+)', note, re.I)
        current = match[1] if match else None
    if current and str(current) in supported:
        return str(current)
    raise ValueError(f'current {dataset} series could not be identified from MoSPI metadata.')


def find_code(meta: dict[str, Any], dimension: str, labels: list[str]) -> tuple[str, str]:
    entries = meta.get(dimension, [])
    if not isinstance(entries, list):
        raise ValueError(f'Missing {dimension} metadata')
    for label in labels:
        matches = [e for e in entries if isinstance(e, dict) and label_key(e.get(f'{dimension}_name', e.get('label', e.get('name')))) == label_key(label)]
        if len(matches) == 1:
            entry = matches[0]
            code = entry.get(f'{dimension}_code', entry.get('code'))
            name = entry.get(f'{dimension}_name', entry.get('label', entry.get('name')))
            if code is not None:
                return str(code), str(name)
    raise ValueError(f'No unambiguous {dimension} code for {labels[0]} in source metadata')


def shift_month(period: str, offset: int) -> str:
    year, month = map(int, period.split('-'))
    year, zero_month = divmod(year * 12 + month - 1 + offset, 12)
    return f'{year:04d}-{zero_month + 1:02d}'


def observation_period(row: dict[str, Any]) -> str | None:
    value = row.get('observation_period', row.get('time_period', row.get('period')))
    if value is not None:
        match = re.fullmatch(r'(\d{4})-M?(\d{1,2})', str(value))
        if match and 1 <= int(match[2]) <= 12:
            return f'{int(match[1]):04d}-{int(match[2]):02d}'
        return None
    try:
        year = int(row['year'])
        month = row.get('month_code', row.get('month'))
        if not str(month).isdigit():
            names = {name.casefold(): i for i, name in enumerate(calendar.month_name) if i}
            names.update({name.casefold(): i for i, name in enumerate(calendar.month_abbr) if i})
            month = names.get(str(month).casefold())
        month = int(month)
        return f'{year:04d}-{month:02d}' if 1 <= month <= 12 and 1900 <= year <= 2200 else None
    except (KeyError, TypeError, ValueError):
        return None


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None
