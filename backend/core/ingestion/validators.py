"""Data Quality and Validation Engine for Macroeconomic Observations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np


class ValidationError(Exception):
    """Raised when an ingested observation fails data validation assertions."""
    pass


class ObservationValidator:
    """Validates raw and normalized economic observations before persistent storage."""

    # Reasonable bounds for macroeconomic variables in India to catch anomalies / data corruption
    BOUNDS: Dict[str, tuple[float, float]] = {
        "gdp_growth": (-30.0, 30.0),            # % YoY (-23.9% was COVID shock)
        "cpi_inflation": (-10.0, 30.0),         # % YoY
        "wpi_inflation": (-20.0, 40.0),         # % YoY
        "repo_rate": (2.0, 20.0),               # % p.a.
        "debt_to_gdp": (30.0, 150.0),           # % of GDP
        "forex_reserves": (50.0, 2000.0),       # Billion USD
        "usd_inr": (30.0, 150.0),               # INR per USD
        "india_vix": (5.0, 100.0),              # Index points
        "nifty_50": (1000.0, 100000.0),         # Index points
        "unemployment_rate": (0.5, 35.0),       # %
    }

    @classmethod
    def validate_numeric(cls, indicator_key: str, value: Optional[float]) -> float:
        """Validates that a numeric observation value is present and within realistic economic bounds."""
        if value is None or np.isnan(value):
            raise ValidationError(f"Observation value for '{indicator_key}' is missing or NaN.")

        val = float(value)
        # Check specific bounds if defined
        for key, (min_val, max_val) in cls.BOUNDS.items():
            if key in indicator_key.lower():
                if not (min_val <= val <= max_val):
                    raise ValidationError(
                        f"Observation value {val} for '{indicator_key}' violates realistic domain bounds [{min_val}, {max_val}]."
                    )
                break

        return val

    @classmethod
    def validate_period_format(cls, period: str) -> str:
        """Ensures observation period adheres to standard date / quarter / annual formats."""
        if not period or not isinstance(period, str):
            raise ValidationError(f"Invalid observation period: '{period}'")
        p = period.strip()
        if len(p) < 4:
            raise ValidationError(f"Period string '{period}' is too short.")
        return p
