---
name: labour-employment-agent
description: Analytical workflows and protocol specifications for Indian formal payroll additions (EPFO), unemployment rates (PLFS), and labour market formalization.
---

# Labour & Employment Macroeconomic Intelligence Skill

## Zero Hardcoded Data & Live API Mandate
- **Strict Prohibition of Hardcoded Values**: Hardcoded payroll counts, mock unemployment figures, or fabricated labour data are strictly prohibited.
- **Live API Ingestion**: All formal payroll metrics (EPFO) and unemployment rates (PLFS) must be retrieved dynamically from live official APIs/portals (e.g., EPFO Monthly Payroll portal, MoSPI e-Sankhyiki / PLFS quarterly bulletins).
- **Explicit Error Handling**: If live labour data cannot be fetched, the tool/agent **must return an explicit, structured error** (`{"status": "error", "error_code": "LIVE_LABOUR_API_UNAVAILABLE", "message": "Failed to fetch live labour metrics from official portal: <details>"}`). It must **never** return fake or hardcoded employment numbers.

## Domain Scope
Monitors formal and informal employment conditions across India:
1. **Formal Payroll Additions**: Monthly Net EPFO (Employees' Provident Fund Organisation) Payroll Additions (`in.macro.labour.epfo_additions`).
2. **Unemployment Trajectory**: Periodic Labour Force Survey (PLFS) Unemployment Rate (`in.macro.labour.unemployment_rate`) and Labour Force Participation Rate (LFPR).
3. **Labour Market Formalization**: Tracking the structural shift from agriculture and informal construction toward organized manufacturing and services.

## Key Canonical Indicators
| Indicator ID | Name | Unit | Frequency | Source |
| :--- | :--- | :--- | :--- | :--- |
| `in.macro.labour.epfo_additions` | Net Monthly EPFO Payroll Additions | Net Persons | Monthly | EPFO / MoSPI |
| `in.macro.labour.unemployment_rate` | PLFS Current Weekly Status Unemployment | % | Quarterly | MoSPI |

## Standard Analytical Guidelines
- **Formal Job Creation Velocity**: Net monthly EPFO additions $> 1.2\text{ million}$ indicates healthy formal sector expansion.
- **Youth & Demographic Dividend**: Evaluate PLFS youth unemployment ($15-29$ age bracket) to assess demographic dividend realization.
- **Rural Employment Drag**: Correlate rural MGNREGA work demand with rainfall anomalies to measure agricultural distress buffering.

## FastMCP Tools (`labour_sector_mcp`)
- `get_epfo_payroll_snapshot(params)`: Fetches monthly net EPFO formal payroll additions via live API. Returns explicit error if unavailable.
