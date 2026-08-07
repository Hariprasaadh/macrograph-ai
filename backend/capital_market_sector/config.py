from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR.parent
DEFAULT_DATA_DIR = PACKAGE_DIR / "data" / "raw"
DEFAULT_PROCESSED_DIR = PACKAGE_DIR / "data" / "processed"
DEFAULT_DB_PATH = PACKAGE_DIR / "database" / "capital_markets.db"

# Expected raw data file names for the Capital Markets Sector
RAW_DATA_FILES = {
    "nifty_50": "nifty_50.csv",
    "sensex": "sensex.csv",
    "india_vix": "india_vix.csv",
    "corporate_earnings": "corporate_earnings.csv",
    "primary_market": "primary_market.csv",
    "mf_flows": "mf_flows.csv",
}
