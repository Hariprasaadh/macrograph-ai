"""Live EPFO/PLFS client with canonical DuckDB fallback."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import re
import requests

from core.database.macro_store import macro_store
from ..config import EPFO_INDICATOR, EPFO_URL, PLFS_URL, REQUEST_TIMEOUT, UNEMPLOYMENT_INDICATOR


class LabourDataClient:
    def __init__(self, timeout: int = REQUEST_TIMEOUT) -> None:
        self.timeout = timeout

    def _fallback(self, indicator: str, label: str, unit: str, source: str) -> dict[str, Any]:
        obs = macro_store.get_latest_canonical_observation(indicator)
        if obs:
            return {"status": "success", "indicator": indicator, "label": label,
                    "latest_period": obs.observation_period, "latest_value": obs.value,
                    "unit": unit, "source": source, "data_status": "verified_historical_cache",
                    "provenance_hash": obs.provenance_hash, "retrieved_at": obs.retrieved_timestamp}
        return {"status": "error", "indicator": indicator, "latest_value": None,
                "data_status": "unavailable", "error": f"No live or verified observation for {indicator}."}

    def get_epfo_payroll(self) -> dict[str, Any]:
        try:
            response = requests.get(EPFO_URL, timeout=self.timeout)
            if response.ok:
                # The bulletin is periodically published as HTML/PDF.  Only accept
                # an unambiguous number near the payroll label; never invent data.
                match = re.search(r"(?:net\s+)?payroll(?:\s+additions)?[^0-9]{0,100}([0-9][0-9,]+(?:\.\d+)?)", response.text, re.I)
                if match:
                    value = float(match.group(1).replace(",", ""))
                    period = datetime.now(timezone.utc).date().isoformat()
                    macro_store.insert_observation("labour", "epfo_additions", "Net Payroll", period, value, "workers", "EPFO", "live")
                    series = macro_store.get_time_series("labour", "epfo_additions")
                    momentum = None
                    if len(series) >= 2:
                        previous = float(series.iloc[-2]["value"])
                        if previous:
                            momentum = round((value - previous) / previous * 100, 2)
                    result = {"status": "success", "indicator": EPFO_INDICATOR, "latest_period": period,
                              "latest_value": value, "unit": "workers", "source": "EPFO", "data_status": "live"}
                    if momentum is not None:
                        result["formalization_momentum_yoy_percent"] = momentum
                    return result
        except Exception as exc:
            live_error = str(exc)
        else:
            live_error = f"EPFO endpoint returned a non-success response."
        result = self._fallback(EPFO_INDICATOR, "Net Monthly EPFO Payroll Additions", "workers", "EPFO")
        if result["status"] == "error":
            result["error"] = live_error
        return result

    def get_unemployment_rate(self) -> dict[str, Any]:
        # PLFS is published as official reports; parsing is deliberately strict.
        try:
            response = requests.get(PLFS_URL, timeout=self.timeout)
            if response.ok:
                match = re.search(r"unemployment rate[^0-9]{0,80}([0-9]+(?:\.\d+)?)", response.text, re.I)
                if match:
                    value = float(match.group(1))
                    return {"status": "success", "indicator": UNEMPLOYMENT_INDICATOR,
                            "latest_period": datetime.now(timezone.utc).year, "latest_value": value,
                            "unit": "%", "source": "MoSPI PLFS", "data_status": "live"}
        except Exception as exc:
            error = str(exc)
        else:
            error = "PLFS endpoint returned no unambiguous unemployment observation."
        result = self._fallback(UNEMPLOYMENT_INDICATOR, "PLFS Unemployment Rate", "%", "MoSPI PLFS")
        if result["status"] == "error":
            result["error"] = error
        return result
