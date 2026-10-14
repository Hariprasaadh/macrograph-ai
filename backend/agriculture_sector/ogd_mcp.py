"""Bounded Agriculture access through the vendored data.gov.in MCP tools."""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone

from fastmcp import Client

from core.config import settings
from data_gov_in_mcp import server as ogd_server
from .client import SourcePayload, SourceUnavailable, ToolBinding
from .data_gov_resources import CROP, MANDI, ResourceSpec
from .models import AgricultureQuery

PAGE_SIZE = 100  # The existing MCP's configured maximum.
MAX_ROWS = 5000


def _decoded(result: object) -> dict:
    if getattr(result, "is_error", False):
        raise SourceUnavailable("Data.gov.in MCP tool failed", "source_error")
    content = getattr(result, "structured_content", None)
    if isinstance(content, dict) and "result" in content:
        content = content["result"]
    if content is None:
        blocks = getattr(result, "content", [])
        content = next((b.text for b in blocks if hasattr(b, "text")), None)
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except ValueError as exc:
            raise SourceUnavailable("Data.gov.in MCP returned invalid JSON", "invalid_data") from exc
    if not isinstance(content, dict):
        raise SourceUnavailable("Data.gov.in MCP returned an invalid object", "invalid_data")
    if content.get("error"):
        raise SourceUnavailable(f"Data.gov.in MCP: {content['error']}", "source_error")
    return content


async def _call(session: Client, name: str, arguments: dict) -> dict:
    try:
        return _decoded(await session.call_tool(name, arguments))
    except SourceUnavailable:
        raise
    except TimeoutError:
        raise
    except Exception as exc:
        raise SourceUnavailable(f"Data.gov.in MCP {name} failed ({type(exc).__name__})", "source_error") from exc


def _field_ids(fields: list) -> set[str]:
    return {str(field.get("id") or field.get("name")) for field in fields if isinstance(field, dict)}


def _validate(spec: ResourceSpec, summary: dict, schema: dict, sample: dict) -> None:
    if summary.get("resource_id") != spec.resource_id or schema.get("resource_id") != spec.resource_id:
        raise SourceUnavailable("Data.gov.in MCP returned a different resource", "invalid_data")
    fields = _field_ids(schema.get("fields", []))
    missing = spec.required_fields - fields
    if missing:
        raise SourceUnavailable(f"{spec.title} is missing source fields: {', '.join(sorted(missing))}", "invalid_data")
    rows = sample.get("records", [])
    if not rows or not isinstance(rows[0], dict) or not spec.required_fields <= rows[0].keys():
        raise SourceUnavailable(f"{spec.title} has no valid sample record", "invalid_data")


def _valid_page(data: dict, expected_id: str, offset: int) -> tuple[list[dict], int]:
    if data.get("resource_id") != expected_id or data.get("offset") != offset:
        raise SourceUnavailable("Data.gov.in MCP pagination returned a different resource/page", "invalid_data")
    rows = data.get("records")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise SourceUnavailable("Data.gov.in MCP page has invalid records", "invalid_data")
    try:
        total = int(data["total_records"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SourceUnavailable("Data.gov.in MCP omitted the filtered record count", "invalid_data") from exc
    if total < 0 or not math.isfinite(total):
        raise SourceUnavailable("Data.gov.in MCP returned an invalid count", "invalid_data")
    return rows, total


async def _pages(session: Client, spec: ResourceSpec, filters: dict[str, str],
                 sort: dict[str, str] | None = None) -> list[dict]:
    collected: list[dict] = []
    seen: set[str] = set()
    offset = 0
    total: int | None = None
    while total is None or offset < total:
        args = {"resource_id": spec.resource_id, "limit": PAGE_SIZE, "offset": offset,
                "filters": json.dumps(filters)}
        if sort:
            args["sort"] = json.dumps(sort)
        data = await _call(session, "get_dataset", args)
        rows, count = _valid_page(data, spec.resource_id, offset)
        if total is None:
            total = count
            if total > MAX_ROWS:
                raise SourceUnavailable(
                    f"{spec.title} has {total} matching rows; narrow the crop, year or geography", "unsupported")
        elif count != total:
            raise SourceUnavailable("Data.gov.in result count changed during pagination", "invalid_data")
        if not rows and offset < total:
            raise SourceUnavailable("Data.gov.in returned an empty page before the end", "invalid_data")
        for row in rows:
            fingerprint = json.dumps(row, sort_keys=True)
            if fingerprint in seen:
                raise SourceUnavailable("Data.gov.in returned duplicate or repeated pages", "invalid_data")
            seen.add(fingerprint)
            collected.append(row)
        offset += len(rows)
        if offset > total:
            raise SourceUnavailable("Data.gov.in returned more rows than its count", "invalid_data")
    return collected


def _year(value: object) -> int:
    try:
        year = int(float(value))
    except (ValueError, TypeError) as exc:
        raise SourceUnavailable("Crop year is invalid", "invalid_data") from exc
    if year < 1900 or year > 2100:
        raise SourceUnavailable("Crop year is outside the expected range", "invalid_data")
    return year


async def fetch_ogd(operation: str, query: AgricultureQuery) -> SourcePayload:
    key = settings.DATA_GOV_IN_API_KEY.get_secret_value()
    if not key or key == "your_api_key_here":
        raise SourceUnavailable("DATA_GOV_IN_API_KEY is required for data.gov.in MCP", "not_configured")
    crop_operation = operation in {"crop_production", "crop_area", "crop_yield", "get_production_trend",
                                   "get_state_crop_production"}
    if not crop_operation and operation not in {"mandi_price", "get_mandi_price_trend", "compare_mandi_prices"}:
        raise SourceUnavailable(f"No configured data.gov.in resource supports {operation}", "unsupported")
    spec = CROP if crop_operation else MANDI
    commodity = (query.crop or query.commodity) if crop_operation else (query.commodity or query.crop)
    if not commodity:
        raise SourceUnavailable("Supply a crop or commodity to select bounded source records", "missing_data")
    if not re.fullmatch(r"[A-Za-z][A-Za-z .()/-]{0,79}", commodity):
        raise SourceUnavailable("Crop or commodity name is invalid", "invalid_data")
    filters = {"crop" if crop_operation else "commodity": commodity.title()}
    if query.state:
        filters["state_name" if crop_operation else "state"] = query.state
    if query.district:
        filters["district_name" if crop_operation else "district"] = query.district
    if query.market and not crop_operation:
        filters["market"] = query.market

    ogd_server.configure_client(key)
    async with Client(ogd_server.mcp, timeout=settings.AGRICULTURE_MCP_TIMEOUT) as session:
        summary = await _call(session, "get_dataset_summary", {"resource_id": spec.resource_id})
        schema = await _call(session, "get_dataset_fields", {"resource_id": spec.resource_id})
        sample = await _call(session, "get_dataset", {"resource_id": spec.resource_id, "limit": 1})
        _validate(spec, summary, schema, sample)
        if crop_operation:
            newest = await _call(session, "get_dataset", {
                "resource_id": spec.resource_id, "limit": 1,
                "filters": json.dumps(filters), "sort": json.dumps({"crop_year": "desc"})})
            newest_rows, _ = _valid_page(newest, spec.resource_id, 0)
            if not newest_rows:
                raise SourceUnavailable(f"No {commodity} crop records are in the configured resource", "missing_data")
            latest = _year(newest_rows[0]["crop_year"])
            if query.period and re.fullmatch(r"\d{4}", query.period):
                years = [int(query.period)]
            elif query.start_year or query.end_year:
                start = query.start_year or query.end_year
                end = query.end_year or query.start_year
                if start > end or end - start > 10:
                    raise SourceUnavailable("Choose an ordered crop-year range of at most 11 years", "unsupported")
                years = list(range(start, end + 1))
            elif operation == "get_production_trend" or query.intent == "crop_production_history":
                years = list(range(max(1997, latest - (query.history_years or 2) + 1), latest + 1))
            else:
                years = [latest]
            if max(years) > latest:
                raise SourceUnavailable(f"Requested crop year is absent; newest {commodity} year is {latest}", "missing_data")
            rows: list[dict] = []
            for year in years:
                year_rows = await _pages(session, spec, {**filters, "crop_year": str(year)})
                if not year_rows:
                    raise SourceUnavailable(f"No {commodity} crop observations for requested year {year}", "missing_data")
                if any(_year(row.get("crop_year")) != year for row in year_rows):
                    raise SourceUnavailable("Data.gov.in ignored the requested crop-year filter", "invalid_data")
                rows.extend(year_rows)
        else:
            rows = await _pages(session, spec, filters)
            if not rows:
                raise SourceUnavailable(f"No {commodity} mandi observations match the requested scope", "missing_data")
    mapping = ({"state": "state_name", "district": "district_name", "period": "crop_year",
                "crop": "crop", "season": "season", "value": "area_" if operation == "crop_area" else "production_"}
               if crop_operation else {"period": "arrival_date", "value": "modal_price"})
    if operation == "crop_yield":
        derived = []
        for row in rows:
            try:
                area, production = float(row["area_"]), float(row["production_"])
            except (KeyError, ValueError, TypeError):
                continue
            if area > 0 and production >= 0:
                derived.append({**row, "derived_yield": production / area,
                                "source_note": "Calculated production_ tonnes / area_ hectares"})
        rows = derived
        mapping["value"] = "derived_yield"
    return SourcePayload(
        data={"records": rows}, source=spec.publisher, category="data_gov",
        binding=ToolBinding(tool="get_dataset", dataset=f"{spec.title} [{spec.resource_id}]",
                            source_url=spec.api_url, arguments={"resource_id": spec.resource_id,
                            "filters": filters, "requested_period": query.period,
                            "start_year": query.start_year, "end_year": query.end_year,
                            "source_fields": mapping},
                            fields=mapping, unit=("tonnes/hectare" if operation == "crop_yield" else
                                                   "hectare" if operation == "crop_area" else spec.unit),
                            frequency=spec.frequency),
        retrieved_at=datetime.now(timezone.utc),
    )
