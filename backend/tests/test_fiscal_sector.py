"""Root test proxy for the Fiscal & Public Finance Sector.

Points pytest to fiscal_sector/tests/test_fiscal_sector.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = str(Path(__file__).parents[1])
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fiscal_sector.tests.test_fiscal_sector import *  # noqa: F401, F403
