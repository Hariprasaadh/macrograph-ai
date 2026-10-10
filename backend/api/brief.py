"""Daily Early-Warning Brief endpoints (Idea 7)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.briefing import store
from core.briefing.job import run_daily_brief, today_ist

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Brief"])
_lock = asyncio.Lock()
_DEBOUNCE_SECONDS = 15 * 60


class BriefRunRequest(BaseModel):
    force: bool = False


def _envelope(brief: Dict[str, Any] | None, cached: bool = False) -> Dict[str, Any]:
    stale = brief is None or brief.get("date") != today_ist()
    if brief is not None:
        brief = {**brief, "provenance": {**brief.get("provenance", {}), "served_from_cache": cached, "is_stale": stale}}
    return {"brief": brief, "last_run_at": brief.get("created_at") if brief else None,
            "is_stale": stale, "served_from_cache": cached}


@router.get("/api/v1/brief/today")
async def brief_today() -> Dict[str, Any]:
    brief = await asyncio.to_thread(store.get_brief, today_ist())
    if brief is None:
        brief = await asyncio.to_thread(store.get_latest_brief)
    return _envelope(brief, cached=True)


@router.post("/api/v1/brief/run")
async def brief_run(request: BriefRunRequest | None = None) -> Dict[str, Any]:
    force = bool(request and request.force)
    if _lock.locked():
        raise HTTPException(status_code=409, detail="A brief run is already in progress.")
    async with _lock:
        existing = await asyncio.to_thread(store.get_brief, today_ist())
        if existing and not force:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(existing["created_at"])).total_seconds()
            if age < _DEBOUNCE_SECONDS:
                return _envelope(existing, cached=True)
        try:
            brief = await run_daily_brief(force=True)
        except Exception:  # noqa: BLE001
            logger.exception("brief run failed")
            raise HTTPException(status_code=500, detail="Brief generation failed.")
        return _envelope(brief, cached=False)


@router.get("/api/v1/brief/history")
async def brief_history(limit: int = 7) -> Dict[str, Any]:
    return {"briefs": await asyncio.to_thread(store.list_briefs, limit)}
