"""Granger testing and deterministic shock simulation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.econometrics.causal_engine import causal_engine

BRENT = "in.macro.prices.brent_crude"
CPI = "in.macro.prices.cpi_headline"
CREDIT = "in.macro.monetary.bank_credit_growth"


def _lagged_pair(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    x = rng.normal(size=n)
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = 0.8 * x[t - 1] + 0.1 * rng.normal()
    return pd.DataFrame({"x": x, "y": y})


def test_granger_missing_columns():
    res = causal_engine.test_granger_causality(pd.DataFrame({"a": [1.0]}), "a", "b")
    assert res == {"is_significant": False, "p_value": None, "optimal_lag": None, "error": "Columns not found"}


def test_granger_insufficient_sample():
    df = pd.DataFrame({"x": range(5), "y": range(5)})
    res = causal_engine.test_granger_causality(df, "x", "y")
    assert res["is_significant"] is False
    assert res["error"] == "Insufficient sample size (N < 10)"
    assert res["cause"] == "x" and res["effect"] == "y"


def test_granger_significant_and_not():
    df = _lagged_pair()
    forward = causal_engine.test_granger_causality(df, "x", "y")
    assert forward["is_significant"] is True
    assert forward["p_value"] < 0.05
    assert forward["optimal_lag"] in (1, 2)
    noise = pd.DataFrame(np.random.default_rng(3).normal(size=(120, 2)), columns=["a", "b"])
    assert causal_engine.test_granger_causality(noise, "a", "b")["is_significant"] is False


def test_granger_exception_is_caught():
    df = pd.DataFrame({"x": [1.0] * 20, "y": [1.0] * 20})
    res = causal_engine.test_granger_causality(df, "x", "y")
    assert res["is_significant"] is False
    assert res["p_value"] is None
    assert "error" in res


def test_simulation_sign_propagation_and_bands():
    res = causal_engine.simulate_scenario("Oil Surge", BRENT, 20)
    impacts = res.forecasted_impacts
    assert impacts[BRENT]["delta"] == 20
    assert impacts[BRENT]["baseline"] == 78.50
    assert impacts[CPI]["delta"] > 0
    assert impacts[CREDIT]["delta"] < 0
    for target, impact in impacts.items():
        if target == BRENT:
            continue
        low, high = impact["confidence_band"]
        # low and high are each rounded to 2 decimals, so the width matches |delta| * 0.5 within 0.01
        assert abs((high - low) - abs(impact["delta"]) * 0.5) <= 0.011
        assert set(impact) == {
            "indicator_name", "sector", "baseline", "shocked_peak", "delta", "confidence_band",
            "transmission_lag_months", "confidence_score", "mechanism_summary",
        }


def test_simulation_constants_are_fixed():
    res = causal_engine.simulate_scenario("Oil", BRENT, 20)
    wpi = res.forecasted_impacts["in.macro.prices.wpi_all"]
    assert wpi["delta"] == round(20 * (0.55 * 0.95) * 0.15, 2)


def test_provenance_is_unique_and_ordered():
    res = causal_engine.simulate_scenario("Oil", BRENT, 20)
    assert res.provenance_chain
    assert len(res.provenance_chain) == len(set(res.provenance_chain))
    assert res.provenance_chain == causal_engine.simulate_scenario("Oil", BRENT, 20).provenance_chain


def test_unknown_shock_variable_is_safe():
    res = causal_engine.simulate_scenario("x", "foo", 5)
    assert res.forecasted_impacts["foo"]["baseline"] == 100.0
    assert res.provenance_chain == []
