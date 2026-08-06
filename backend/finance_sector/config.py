from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR.parent
DEFAULT_CACHE_DIR = PACKAGE_DIR / "data" / "cache"

MOSPI_POWERBI_ENDPOINT = "https://wabi-india-central-a-primary-api.analysis.windows.net/public/reports/querydata?synchronous=true"
MOSPI_SCHEMA_ENDPOINT = "https://wabi-india-central-a-primary-api.analysis.windows.net/public/reports/conceptualschema"
MOSPI_RESOURCE_KEY = "6718eb92-26e6-4c7b-830d-cd1d949ad14e"
MOSPI_DATASET_ID = "59f41f3a-e572-482c-b40f-b2fdea51a2a6"
MOSPI_REPORT_ID = "80b57b61-c05b-41c1-9aa1-3e1273337d84"

WORLD_BANK_API_BASE = "http://api.worldbank.org/v2/country/IND/indicator"
IMF_API_BASE = "https://www.imf.org/external/datamapper/api/v1"
FRED_GRAPH_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
