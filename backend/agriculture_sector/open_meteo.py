"""Verified Open-Meteo geocoding and dated weather observations."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from .client import SourcePayload, SourceUnavailable, ToolBinding
from .models import AgricultureQuery

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
DAILY = {
    "temperature_2m_min": ("temperature_min", "°C"),
    "temperature_2m_max": ("temperature_max", "°C"),
    "precipitation_sum": ("precipitation", "mm"),
    "wind_speed_10m_max": ("wind_speed_max", "km/h"),
    "et0_fao_evapotranspiration": ("et0", "mm"),
}
CURRENT = {
    "temperature_2m": ("temperature", "°C"),
    "relative_humidity_2m": ("relative_humidity", "%"),
    "precipitation": ("precipitation", "mm"),
    "wind_speed_10m": ("wind_speed", "km/h"),
}


async def _json(client: httpx.AsyncClient, url: str, params: dict) -> dict:
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        body = response.json()
    except httpx.TimeoutException as exc:
        raise TimeoutError("Open-Meteo request timed out") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise SourceUnavailable(f"Open-Meteo request failed ({type(exc).__name__})", "source_error") from exc
    if not isinstance(body, dict) or body.get("error"):
        raise SourceUnavailable("Open-Meteo rejected the weather request", "source_error")
    return body


async def fetch_open_meteo(operation: str, query: AgricultureQuery) -> SourcePayload:
    place = query.location or query.city or query.state
    if not place:
        raise SourceUnavailable("Supply a city or location for weather data", "missing_data")
    historical = operation in {"weather_historical", "rainfall", "weather_agriculture"}
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    start = query.start_date or (today - timedelta(days=query.days))
    end = query.end_date or (today - timedelta(days=1))
    if historical and (end < start or (end - start).days > 365):
        raise SourceUnavailable("Choose a weather range of at most 366 days", "unsupported")
    async with httpx.AsyncClient(timeout=30, headers={"Accept": "application/json"}) as client:
        geo = await _json(client, GEOCODE, {"name": place, "count": 10,
                                            "countryCode": "IN", "language": "en"})
        candidates = [row for row in geo.get("results", [])
                      if isinstance(row, dict) and row.get("country_code") == "IN"
                      and row.get("latitude") is not None and row.get("longitude") is not None]
        exact = [row for row in candidates if row.get("name", "").casefold() == place.casefold()]
        if not exact:
            raise SourceUnavailable(f"Could not resolve Indian location: {place}", "missing_data")
        location = exact[0]
        url = ARCHIVE if historical else FORECAST
        params = {"latitude": location["latitude"], "longitude": location["longitude"],
                  "timezone": "Asia/Kolkata"}
        if historical:
            params.update({"start_date": start.isoformat(), "end_date": end.isoformat(),
                           "daily": ",".join(DAILY)})
        elif operation == "weather_current":
            params["current"] = ",".join(CURRENT)
        else:
            params["daily"] = ",".join(DAILY)
            params["forecast_days"] = min(query.days, 16)
        body = await _json(client, url, params)
    label = ", ".join(str(location.get(k)) for k in ("name", "admin1", "country") if location.get(k))
    if operation == "weather_current":
        current, units = body.get("current"), body.get("current_units", {})
        if not isinstance(current, dict) or not current.get("time"):
            raise SourceUnavailable("Open-Meteo returned no current observation time", "missing_data")
        rows = []
        for source_field, (metric, unit) in CURRENT.items():
            value = current.get(source_field)
            if value is None:
                continue
            if units.get(source_field) != unit:
                raise SourceUnavailable(f"Open-Meteo changed {source_field} units", "invalid_data")
            rows.append({"period": current["time"], "metric": metric, "value": value,
                         "unit": unit, "frequency": "current", "location": place,
                         "display_name": label, "latitude": location["latitude"],
                         "longitude": location["longitude"],
                         "indicator": metric.replace("_", " "),
                         "source_note": "Open-Meteo modelled current conditions at the reference coordinate."})
        if not rows:
            raise SourceUnavailable("Open-Meteo returned no current weather values", "missing_data")
        return SourcePayload(data={"records": rows}, source="Open-Meteo", category="weather_mcp",
                             binding=ToolBinding(tool="Open-Meteo current API",
                                                 dataset="Open-Meteo current weather", source_url=url,
                                                 arguments={"location": label, "latitude": location["latitude"],
                                                            "longitude": location["longitude"]},
                                                 frequency="current"),
                             retrieved_at=datetime.now(timezone.utc))
    daily = body.get("daily")
    units = body.get("daily_units", {})
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        raise SourceUnavailable("Open-Meteo returned no dated daily observations", "missing_data")
    dates = daily["time"]
    if historical and dates != [(start + timedelta(days=i)).isoformat()
                                for i in range((end - start).days + 1)]:
        raise SourceUnavailable("Open-Meteo did not return the requested historical dates", "missing_data")
    rows = []
    for source_field, (metric, unit) in DAILY.items():
        values = daily.get(source_field)
        if not isinstance(values, list) or len(values) != len(dates):
            raise SourceUnavailable(f"Open-Meteo omitted {source_field} observations", "missing_data")
        if units.get(source_field) != unit:
            raise SourceUnavailable(f"Open-Meteo changed {source_field} units", "invalid_data")
        for day, value in zip(dates, values):
            if value is None:
                continue
            rows.append({"period": day, "metric": metric, "value": value, "unit": unit,
                         "frequency": "daily", "location": place, "display_name": label,
                         "latitude": location["latitude"], "longitude": location["longitude"],
                         "indicator": metric.replace("_", " "),
                         "source_note": "Open-Meteo grid estimate at the reference coordinate; not an IMD station or city-wide total."})
    if not rows:
        raise SourceUnavailable("Open-Meteo returned only missing daily values", "missing_data")
    if operation == "rainfall" or query.intent == "rainfall_only":
        rows = [{**row, "city": location["name"]} for row in rows if row["metric"] == "precipitation"]
        if not rows:
            raise SourceUnavailable("Open-Meteo returned no precipitation observations", "missing_data")
    return SourcePayload(data={"records": rows}, source="Open-Meteo", category="weather_mcp",
                         binding=ToolBinding(tool="Open-Meteo daily API", dataset="Open-Meteo daily weather",
                                             source_url=url, arguments={"location": label,
                                             "latitude": location["latitude"],
                                             "longitude": location["longitude"],
                                             "start_date": start.isoformat() if historical else None,
                                             "end_date": end.isoformat() if historical else None},
                                             frequency="daily"),
                         retrieved_at=datetime.now(timezone.utc))
