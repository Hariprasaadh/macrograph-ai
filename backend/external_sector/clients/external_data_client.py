from __future__ import annotations
from typing import Any
from datetime import datetime,timezone
import requests
from core.database.macro_store import macro_store
from ..config import *
class ExternalDataClient:
 def __init__(self,timeout=REQUEST_TIMEOUT): self.timeout=timeout
 def _cache(self,ind,label,unit,source):
  obs=macro_store.get_latest_canonical_observation(ind)
  if obs:return {"status":"success","indicator":ind,"label":label,"latest_period":obs.observation_period,"latest_value":obs.value,"unit":unit,"source":source,"data_status":"verified_historical_cache","provenance_hash":obs.provenance_hash}
  return {"status":"error","indicator":ind,"latest_value":None,"data_status":"unavailable","error":f"No live or verified observation for {ind}."}
 def get_exchange_rate(self):
  try:
   import yfinance as yf
   close=yf.Ticker(YAHOO_SYMBOL).history(period="5d")["Close"].dropna()
   if not close.empty:
    value=float(close.iloc[-1]); return {"status":"success","indicator":EXCHANGE_INDICATOR,"latest_period":str(close.index[-1].date()),"latest_value":round(value,4),"unit":"INR/USD","source":"Yahoo Finance INR=X","data_status":"live"}
  except Exception as exc: error=str(exc)
  else: error="Yahoo Finance returned no exchange-rate observations."
  result=self._cache(EXCHANGE_INDICATOR,"USD/INR","INR/USD","RBI")
  if result.get("status") == "error":
   result=self._cache("in.macro.external.usd_inr","USD/INR","INR/USD","RBI")
  result.setdefault("error",error); return result
 def _read(self,ind,label,unit,source,url):
  result=self._cache(ind,label,unit,source)
  try:
   result["live_endpoint_reachable"]=requests.get(url,timeout=self.timeout).ok
  except Exception as exc: result["live_error"]=str(exc)
  return result
 def get_forex_reserves(self):
  result=self._read(FOREX_INDICATOR,"Foreign Exchange Reserves","Billion USD","RBI",RBI_URL)
  imports=macro_store.get_latest_canonical_observation(IMPORTS_INDICATOR)
  result["import_cover_months"] = round(float(result["latest_value"])/float(imports.value),2) if result.get("latest_value") is not None and imports and imports.value else None
  result["import_cover_status"] = "computed_from_verified_monthly_imports" if result["import_cover_months"] is not None else "unavailable_without_verified_monthly_imports_series"
  return result
 def get_trade_balance(self): return self._read(TRADE_INDICATOR,"Merchandise Trade Balance","Billion USD","Ministry of Commerce",TRADE_URL)
 def get_current_account_deficit(self): return self._cache(CAD_INDICATOR,"Current Account Deficit","% of GDP","RBI")
