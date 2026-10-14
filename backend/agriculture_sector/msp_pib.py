"""Read the latest verified MSP table from an official PIB release."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from .client import SourcePayload, SourceUnavailable, ToolBinding
from .models import AgricultureQuery

# Official announcement URL, not a stored price. Source numbers are fetched
# and parsed from the live table; a newer season requires a new verified URL.
RABI_RELEASE_URL = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2316956&lang=2&reg=48"
RABI_SEASON = "2027-28"


async def fetch_rabi_msp(query: AgricultureQuery) -> SourcePayload:
    crop = query.crop or query.commodity
    if not crop:
        raise SourceUnavailable("Supply a crop for MSP lookup", "missing_data")
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            response = await client.get(RABI_RELEASE_URL)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise TimeoutError("Official MSP release timed out") from exc
    except httpx.HTTPError as exc:
        raise SourceUnavailable(f"Official MSP release request failed ({type(exc).__name__})", "source_error") from exc
    document = BeautifulSoup(response.text, "html.parser")
    full_text = document.get_text(" ", strip=True)
    if "Ministry of Agriculture" not in full_text or "Minimum Support Prices" not in full_text:
        raise SourceUnavailable("Official MSP release identity could not be verified", "invalid_data")
    table = next((table for table in document.find_all("table")
                  if f"MSP RMS {RABI_SEASON}" in table.get_text(" ", strip=True)), None)
    if table is None:
        raise SourceUnavailable("Official MSP table or marketing season changed", "invalid_data")
    lines = [[cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
             for row in table.find_all("tr")]
    if not lines or len(lines[0]) < 6 or "Crops" not in lines[0][1]:
        raise SourceUnavailable("Official MSP table columns changed", "invalid_data")
    matches = [line for line in lines[1:] if len(line) >= 6 and line[1].casefold() == crop.casefold()]
    if len(matches) != 1:
        raise SourceUnavailable(f"Official Rabi MSP table has no unique crop named {crop}", "missing_data")
    row = matches[0]
    values = []
    for index in (2, 5):
        try:
            value = float(row[index].replace(",", ""))
        except (ValueError, IndexError) as exc:
            raise SourceUnavailable("Official MSP table has a nonnumeric price", "invalid_data") from exc
        if value <= 0:
            raise SourceUnavailable("Official MSP table has a nonpositive price", "invalid_data")
        values.append(value)
    previous = re.search(r"MSP RMS (\d{4}-\d{2})", lines[0][5])
    if previous is None:
        raise SourceUnavailable("Previous MSP season could not be read", "invalid_data")
    requested = query.period
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    active_start = today.year if today.month >= 4 else today.year - 1
    active_season = f"{active_start}-{(active_start + 1) % 100:02d}"
    if int(RABI_SEASON[:4]) < active_start:
        raise SourceUnavailable("Configured official MSP release is older than the active marketing season", "missing_data")
    records = [
        {"crop": row[1], "period": RABI_SEASON, "season": "Rabi",
         "msp": values[0], "unit": "INR/quintal", "frequency": "marketing season",
         "source_note": "Latest approved Rabi marketing season; announcement is distinct from the active marketing season."},
        {"crop": row[1], "period": previous[1], "season": "Rabi",
         "msp": values[1], "unit": "INR/quintal", "frequency": "marketing season",
         "source_note": ("Active Rabi marketing season as of retrieval date."
                         if previous[1] == active_season else
                         "Previous Rabi marketing season, shown for context in the same official table.")},
    ]
    if requested:
        records = [item for item in records if item["period"] == requested]
        if not records:
            raise SourceUnavailable(f"Official MSP table does not contain requested season {requested}", "missing_data")
    return SourcePayload(data={"records": records},
                         source="Ministry of Agriculture and Farmers Welfare via Press Information Bureau",
                         category="pib",
                         binding=ToolBinding(tool="official_PIB_MSP_table",
                                             dataset=f"Minimum Support Prices for Rabi Crops, RMS {RABI_SEASON}",
                                             source_url=RABI_RELEASE_URL,
                                             arguments={"crop": crop, "marketing_season": RABI_SEASON,
                                                        "source_fields": ["Crops", f"MSP RMS {RABI_SEASON}",
                                                                          f"MSP RMS {previous[1]}"]},
                                             unit="INR/quintal", frequency="marketing season"),
                         retrieved_at=datetime.now(timezone.utc))
