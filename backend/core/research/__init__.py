"""Research-lab layer: pure functions over the frozen KG / engine / A2A outputs. Never mutates engine state."""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Mirrors the literals in core/econometrics/causal_engine.py (pinned by test_causal_engine.py).
ATTENUATION = 0.55
SCALE = 0.15
BAND = 0.25

UNUSABLE_STATUSES = ("unavailable", "unspecified", None)


def safe_extra(name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Optional[Any]:
    """Best-effort builder: any exception is logged and the key is simply omitted."""
    try:
        return fn(*args, **kwargs)
    except Exception:  # noqa: BLE001 - extras must never break the primary response
        logger.exception("Optional payload '%s' skipped", name)
        return None
