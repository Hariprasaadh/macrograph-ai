from __future__ import annotations

from typing import Any, Dict, List, Optional


class FinanceAgent:
    """Base class for Finance Sector domain analyzers."""
    name = "finance"

    def analyze(self, options: Optional[Any] = None) -> Any:
        raise NotImplementedError
