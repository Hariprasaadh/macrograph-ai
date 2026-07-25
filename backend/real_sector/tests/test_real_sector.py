from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from real_sector.agents.tools import SectorToolRegistry
from real_sector.config import DEFAULT_DATA_DIR
from real_sector.services.pipeline import RealSectorPipeline


class RealSectorPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = RealSectorPipeline(DEFAULT_DATA_DIR)
        cls.tables = cls.pipeline.refresh(persist=False)

    def test_all_available_source_areas_are_ingested(self) -> None:
        self.assertGreater(len(self.tables["agri_production"]), 0)
        self.assertGreater(len(self.tables["industry_iip"]), 0)
        self.assertGreater(len(self.tables["gdp_quarterly"]), 0)
        self.assertGreater(len(self.tables["cpi_combined"]), 0)
        self.assertGreater(len(self.tables["wpi_monthly"]), 0)

    def test_each_sector_is_exposed_as_a_separate_llm_tool(self) -> None:
        registry = SectorToolRegistry(self.pipeline)
        names = {item["function"]["name"] for item in registry.openai_functions()}
        self.assertEqual(names, {"get_agriculture_snapshot", "get_industry_snapshot", "get_national_income_snapshot", "get_prices_snapshot"})
        for name in names:
            response = registry.invoke(name)
            self.assertEqual(response.agent, name.removeprefix("get_").removesuffix("_snapshot"))


if __name__ == "__main__":
    unittest.main()
