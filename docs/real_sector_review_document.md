cd

# Real Sector Review Document

## 1. Purpose

This document reviews the Real Sector module of MacroGraph AI. The focus is on how the system captures, processes, analyzes, and explains the real side of the Indian economy through national income, industrial production, prices and inflation, and agriculture indicators.

The Real Sector Agent is designed as a domain-specific macroeconomic intelligence component. It converts official workbook-based datasets into normalized tables, exposes analytical tools through A2A and MCP-compatible interfaces, and generates an integrated economic reasoning report for downstream dashboard or orchestration use.

## 2. Scope of Real Sector Coverage

The module currently covers four major real-sector dimensions:

| Area                  | Main Indicators                                          | Analytical Purpose                                                                 |
| --------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| National income       | Real GDP, nominal GDP, Gross Fixed Capital Formation     | Measures output growth, demand strength, and investment momentum                   |
| Industrial production | IIP growth, manufacturing index                          | Tracks production activity and manufacturing-cycle health                          |
| Prices and inflation  | Headline CPI, food CPI, core CPI, WPI, house price index | Assesses consumer-price pressure, wholesale cost pressure, and asset-price signals |
| Agriculture           | Foodgrain production, foodgrain yield, MSP               | Identifies supply-side food inflation risk and rural-sector stress                 |

This coverage is appropriate for a macroeconomic platform because real-sector conditions form the base layer for monetary policy, fiscal planning, financial-market sentiment, and household welfare analysis.

## 3. System Design Summary

The Real Sector module is implemented as an independent agent under `backend/real_sector`. It follows a clean layered structure:

| Layer               | Responsibility                                                                            |
| ------------------- | ----------------------------------------------------------------------------------------- |
| Raw data layer      | Stores untouched official workbooks under`backend/real_sector/data/raw`                 |
| Preprocessing layer | Converts workbooks into normalized CSV tables under`backend/real_sector/data/processed` |
| Pipeline service    | Loads and refreshes cleaned tables through`RealSectorPipeline`                          |
| Domain agents       | Run deterministic indicator analysis for income, industry, prices, and agriculture        |
| Tool registry       | Exposes domain analyses as callable tools                                                 |
| Protocol layer      | Supports A2A task execution and MCP JSON-RPC tool calls                                   |
| API layer           | Provides REST endpoints for agent-card discovery, tool calls, and pipeline refresh        |

The design is suitable for a multi-agent macroeconomic system because each domain agent has a clear boundary while still supporting integrated synthesis through `real_sector_comprehensive_synthesis`.

## 4. Exposed Agent Capabilities

The Real Sector Agent advertises the following skills:

| Skill ID                                | Description                                                                  |
| --------------------------------------- | ---------------------------------------------------------------------------- |
| `national_income_analysis`            | Analyzes quarterly real GDP, nominal GDP, and Gross Fixed Capital Formation  |
| `industrial_production_analysis`      | Evaluates IIP use-based indicators and manufacturing output                  |
| `price_inflation_analysis`            | Monitors headline CPI, food CPI, core CPI, WPI, and house price index        |
| `agricultural_snapshot`               | Monitors foodgrain production, yield, and Minimum Support Prices             |
| `real_sector_comprehensive_synthesis` | Produces an integrated macroeconomic report using all real-sector indicators |

The module also exposes callable tools:

| Tool                             | Function                                      |
| -------------------------------- | --------------------------------------------- |
| `get_national_income_snapshot` | Summarizes GDP, nominal GDP, and GFCF         |
| `get_industry_snapshot`        | Summarizes IIP and manufacturing signals      |
| `get_prices_snapshot`          | Summarizes CPI, WPI, and house-price signals  |
| `get_agriculture_snapshot`     | Summarizes production, yield, and MSP signals |

## 5. Latest Local Indicator Snapshot

The following results were generated from the local demo run using the processed datasets available in the repository.

| Segment              | Latest Period | Key Reading                                    | Interpretation                                        |
| -------------------- | ------------- | ---------------------------------------------- | ----------------------------------------------------- |
| Real GDP             | 2026-03-01    | 7.83% year-on-year growth                      | Output momentum is classified as growing              |
| Nominal GDP          | 2026-03-01    | 9.12% year-on-year growth                      | Nominal activity is expanding faster than real output |
| GFCF                 | 2026-03-01    | 10.82% year-on-year growth                     | Investment momentum is strong                         |
| IIP growth           | 2026-03-01    | 1.89% latest growth                            | Industrial activity is soft                           |
| Manufacturing index  | 2026-05-01    | 122.6 index value, 4.92% year-on-year growth   | Manufacturing remains expansionary                    |
| Headline CPI         | 2026-06-01    | 4.37% latest growth                            | Consumer inflation is classified as contained         |
| WPI                  | 2026-04-01    | 8.30% latest growth                            | Wholesale price pressure appears elevated             |
| House price index    | 2026-03-01    | 121.52 index value, 10.79% year-on-year growth | Housing prices show firm annual growth                |
| Foodgrain production | 2026-03-01    | -51.55% annual comparison                      | Supply-side agriculture risk is high                  |
| Foodgrain yield      | 2026-03-01    | -10.19% annual comparison                      | Yield deterioration reinforces supply risk            |
| MSP                  | 2026-03-01    | 13.36% annual comparison                       | MSP pressure may add to food-price risk               |

## 6. Economic Interpretation

The real-sector picture is mixed. National income indicators are strong, with real GDP growth and GFCF suggesting healthy aggregate demand and investment momentum. This supports the broader macroeconomic view that India has a resilient output base.

Industrial production is less convincing. IIP growth is positive but weak, while the manufacturing index shows better year-on-year performance. This divergence suggests that the system should avoid treating industry as uniformly strong; the review should distinguish between broad IIP softness and specific manufacturing resilience.

Inflation conditions are classified as contained at the headline CPI level, but WPI and food-related signals require closer attention. Food inflation risk is particularly important because agricultural output and yield signals show sharp declines in the latest annual comparison, while MSP has risen strongly. In a macroeconomic intelligence platform, this combination should trigger a supply-side inflation watch.

The overall real-sector conclusion is that output growth is currently the strongest pillar, industry is moderate, and agriculture-linked price risk is the main vulnerability.

## 7. Architecture Review

### Strengths

- The module has a clean separation between preprocessing, pipeline loading, domain analysis, tool exposure, and protocol handling.
- A2A support makes the Real Sector Agent discoverable and interoperable with a central orchestrator.
- MCP support allows LLM agents to call real-sector tools through a standard tool interface.
- The design is deterministic at the indicator-analysis layer, which improves explainability and reproducibility.
- Source metadata is preserved, including workbook names, observation counts, and latest dates.

### Review Concerns

- Some generated report fields display `None` for latest values when the metric is a direct growth series. The report should prefer `latest_growth_pct` when `latest_value` is absent.
- The CPI output should be validated. In the demo, food CPI and core CPI returned unusually high `latest_growth_pct` values that appear closer to index levels than inflation rates.
- The agriculture production decline of 51.55% is severe and should be checked against the source workbook structure before being used as a final economic conclusion.
- Units should be displayed consistently. GDP and GFCF values currently appear without a clear unit label in the generated Markdown report.
- The industry agent flags IIP softness correctly, but the period-change calculation for direct growth data may exaggerate the movement because it compares growth rates rather than index levels.

## 8. Suggested Improvements

| Priority | Improvement                                                            | Reason                                                         |
| -------- | ---------------------------------------------------------------------- | -------------------------------------------------------------- |
| High     | Fix report formatting for direct-growth metrics                        | Avoid`None` values in generated Markdown output              |
| High     | Add validation rules for CPI, food CPI, core CPI, and WPI fields       | Prevent index levels from being interpreted as inflation rates |
| High     | Add unit metadata for GDP, GFCF, production, yield, and MSP            | Improves reviewer confidence and dashboard clarity             |
| Medium   | Add threshold bands for each indicator                                 | Makes assessments more transparent and defensible              |
| Medium   | Add data-freshness warnings when latest dates differ across indicators | Prevents over-comparing quarterly, monthly, and annual signals |
| Medium   | Include source workbook names in the final Markdown report             | Strengthens auditability                                       |
| Low      | Add charts for GDP, IIP, CPI, and agriculture indicators               | Improves review presentation and dashboard readiness           |

## 9. Review Checklist

| Review Item                                                           | Status            |
| --------------------------------------------------------------------- | ----------------- |
| Real-sector indicators are grouped into logical macroeconomic domains | Complete          |
| Local data pipeline produces processed CSV outputs                    | Complete          |
| A2A agent card exposes real-sector skills                             | Complete          |
| MCP tools are available for LLM/tool-based access                     | Complete          |
| Comprehensive synthesis report is generated                           | Complete          |
| Latest values and source metadata are included in artifacts           | Complete          |
| Direct-growth formatting issue is identified                          | Needs fix         |
| CPI and agriculture extreme values are validated against raw sources  | Needs review      |
| Units are consistently shown in generated reports                     | Needs improvement |

## 10. Conclusion

The Real Sector module provides a solid foundation for MacroGraph AI's macroeconomic intelligence layer. It covers the right core domains, uses a modular agent design, and exposes outputs through modern agent interoperability standards. The current implementation is review-ready from an architectural perspective, but a few data-validation and reporting refinements are recommended before treating the generated economic conclusions as final.

For review presentation, the strongest points to emphasize are the modular real-sector decomposition, the use of official local datasets, A2A/MCP compatibility, and the ability to generate an integrated economic reasoning report. The main improvement area is not the architecture; it is ensuring that all reported indicator values, units, and growth-rate interpretations are economically consistent.
