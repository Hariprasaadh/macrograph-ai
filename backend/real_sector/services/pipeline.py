from __future__ import annotations

from pathlib import Path
from typing import Callable
import pandas as pd

from ..config import DEFAULT_DATA_DIR, DEFAULT_PROCESSED_DIR
from ..preprocess.agriculture_cleaner import clean_agriculture
from ..preprocess.industry_cleaner import clean_industry
from ..preprocess.income_cleaner import clean_income
from ..preprocess.prices_cleaner import clean_prices


class RealSectorPipeline:
    """Loads only local supplied files and exposes normalized tables to agents."""
    def __init__(self, data_dir: Path | str = DEFAULT_DATA_DIR, processed_dir: Path | str = DEFAULT_PROCESSED_DIR) -> None:
        self.data_dir, self.processed_dir = Path(data_dir), Path(processed_dir)
        self._tables: dict[str, pd.DataFrame] | None = None

    def refresh(self, *, persist: bool = True) -> dict[str, pd.DataFrame]:
        if not self.data_dir.is_dir():
            raise FileNotFoundError(f"Data directory is missing: {self.data_dir}")
        tables: dict[str, pd.DataFrame] = {}
        for cleaner in (clean_agriculture, clean_industry, clean_income, clean_prices):
            tables.update(cleaner(self.data_dir))
        if persist:
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            for name, table in tables.items():
                table.to_csv(self.processed_dir / f"{name}.csv", index=False)
        self._tables = tables
        return tables

    def load(self) -> dict[str, pd.DataFrame]:
        return self._tables if self._tables is not None else self.refresh()

    def status(self) -> dict[str, object]:
        tables = self.load()
        return {"data_directory": str(self.data_dir), "tables": {name: len(table) for name, table in tables.items()}}
