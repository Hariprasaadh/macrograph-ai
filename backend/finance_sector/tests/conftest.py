"""pytest configuration for the finance sector test suite."""
from __future__ import annotations

import pytest


# Use auto mode so all async test functions run without explicit decorator
pytest_plugins = ("pytest_asyncio",)
