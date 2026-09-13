from __future__ import annotations
from typing import Any
import requests
from core.database.macro_store import macro_store
from ..config import FOODGRAIN_INDICATOR, MSP_INDICATOR, AGMARKNET_URL, CCEA_URL, REQUEST_TIMEOUT
class AgricultureDataClient:
    def __init__(self, timeout: int = REQUEST_TIMEOUT): self.timeout = timeout
    def _read(self, indicator: str, label: str, unit: str, source: str) -> dict[str, Any]:
        obs = macro_store.get_latest_canonical_observation(indicator)
        if obs: return {"status":"success","indicator":indicator,"label":label,"latest_period":obs.observation_period,"latest_value":obs.value,"unit":unit,"source":source,"data_status":"verified_historical_cache","provenance_hash":obs.provenance_hash}
        return {"status":"error","indicator":indicator,"latest_value":None,"data_status":"unavailable","error":f"No live or verified observation for {indicator}."}
    def _probe(self, url: str, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.ok: fallback["live_endpoint_reachable"] = True
        except Exception as exc: fallback["live_error"] = str(exc)
        return fallback
    def get_foodgrain_production(self): return self._probe(AGMARKNET_URL, self._read(FOODGRAIN_INDICATOR,"Total Foodgrain Production","Million Tonnes","Ministry of Agriculture"))
    def get_msp_growth(self): return self._probe(CCEA_URL, self._read(MSP_INDICATOR,"Average MSP Hike","% YoY","CCEA"))
