"""Deterministic Prices intent; no LLM or economic values."""
from __future__ import annotations

import re
from .models import PriceRequest, PricesIntent


def is_direct_prices_query(query: str) -> bool:
    q = query.casefold()
    prices = re.search(r'\b(cpi|cfpi|wpi|inflation|consumer price index|wholesale price index)\b', q)
    reasoning = re.search(r'\b(why|impacts?|affects?|causes?|drivers?|relationship|correlation|forecast\w*|predict\w*|policy|transmission|explain)\b', q)
    other_sector = re.search(r'\b(gdp|gva|repo|unemployment|nifty|sensex|fiscal|exports?|imports?|monsoon|credit|liquidity)\b', q)
    return bool(prices and not reasoning and not other_sector)


def parse_prices_intent(query: str) -> PricesIntent:
    q = query.casefold()
    source = 'imf' if re.search(r'\bimf\b|international monetary fund', q) else 'mospi'
    countries = [name for name, pattern in [('India', r'\bindia(?:n)?\b'), ('China', r'\bchina\b|\bchinese\b')] if re.search(pattern, q)]
    comparison = len(countries) > 1
    if countries == ['China']:
        source = 'imf'
    errors: list[str] = []
    if comparison and re.search(r'\bmospi\b', q):
        source = 'mospi'
    if not comparison and source == 'imf' and re.search(r'\bmospi\b', q):
        errors.append('A single request cannot select both MoSPI and IMF; request each source separately.')
    lookback = 12
    duration = re.search(r'(?:last|past|previous)\s+(\d+)\s*(months?|years?)', q)
    if duration:
        lookback = int(duration[1]) * (12 if duration[2].startswith('year') else 1)
        if not 1 <= lookback <= 120:
            errors.append('Requested lookback must be between 1 and 120 months.')
            lookback = 12
    trend = bool(duration or re.search(r'\b(trends?|history|historical|monthly|over time)\b', q))
    base = re.search(r'base(?:[ -]year)?\s*(?:=|:|of)?\s*[\'"]?(\d{4}(?:-\d{2})?)', q)
    periods = re.findall(r'\b(20\d{2})-(0[1-9]|1[0-2])\b', q)
    start = end = None
    if periods:
        start, end = '-'.join(periods[0]), '-'.join(periods[-1])
        trend = True
        if start > end:
            errors.append('Start period must not follow end period.')
    elif (years := re.search(r'\b(?:from|in|for)\s+(20\d{2})(?:\s*(?:to|through|-)\s*(20\d{2}))?\b', q)):
        start, end = f'{years[1]}-01', f'{years[2] or years[1]}-12'
        trend = True
    has_wpi = bool(re.search(r'\bwpi\b|wholesale price', q))
    has_cpi = bool(re.search(r'\bcpi\b|\bcfpi\b|consumer price', q)) or not has_wpi
    requests: list[PriceRequest] = []
    if has_cpi:
        categories = []
        for word, category in [('cfpi', 'cfpi'), ('food', 'food'), ('fuel', 'fuel'), ('housing', 'housing'), ('health', 'health'), ('transport', 'transport'), ('core', 'core')]:
            if re.search(rf'\b{word}\b', q):
                categories.append(category)
        if 'cfpi' in categories and 'food' in categories:
            categories.remove('food')
        if 'subgroup' in q and not categories:
            categories = ['food', 'fuel', 'housing', 'health', 'transport']
        sectors = [s for s in ('rural', 'urban', 'combined') if re.search(rf'\b{s}\b', q)]
        # A list such as "food, rural, and urban" asks for food plus two headlines.
        listed_sectors = bool(categories and len(sectors) > 1 and re.search(r'food\s*,', q))
        for category in categories:
            for sector in (['combined'] if listed_sectors else sectors or ['combined']):
                requests.append(PriceRequest(category=category, sector=sector))
        if not categories or listed_sectors or re.search(r'\b(headline|general)\b', q):
            for sector in sectors or ['combined']:
                requests.append(PriceRequest(sector=sector))
    if has_wpi:
        categories = [c for phrase, c in [('primary articles', 'primary'), ('manufactured', 'manufactured'), ('fuel', 'fuel'), ('food', 'food')] if phrase in q]
        for category in categories or ['headline']:
            requests.append(PriceRequest(indicator='wpi', category=category))
    if start and end and (int(end[:4]) - int(start[:4])) * 12 + int(end[5:]) - int(start[5:]) >= 120:
        errors.append('Requested period range exceeds 120 months.')
    return PricesIntent(source=source, operation='comparison' if comparison else 'trend' if trend else 'latest',
                        countries=countries, geography=countries[0] if len(countries) == 1 else 'India', lookback_months=lookback,
                        requests=requests, base_year=base[1] if base else None,
                        start_period=start, end_period=end, errors=errors)
