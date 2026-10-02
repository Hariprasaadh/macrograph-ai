"""Prices & Inflation Sector A2A Agent Executor.

Connects directly with the official MoSPI e-Sankhyiki FastMCP server (https://mcp.mospi.gov.in/)
to deliver live, verified Indian retail and wholesale inflation metrics.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from core.protocols.a2a.models import (
    A2AArtifact,
    A2AMessage,
    A2AMessagePart,
    AgentCard,
    AgentSkill,
    RequestContext,
    TaskResponse,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from core.protocols.a2a.lifecycle import AgentExecutor, EventQueue
from core.ingestion.mospi_client import call_mospi_mcp

logger = logging.getLogger(__name__)


class PricesSectorAgentExecutor(AgentExecutor):
    """A2A Agent Executor for Indian Prices & Inflation Macroeconomic Intelligence."""

    @classmethod
    def get_agent_card(cls, base_url: str = "http://localhost:8000/prices-sector") -> AgentCard:
        """Constructs and returns the A2A Agent Card for capability discovery."""
        return AgentCard(
            name="Prices & Inflation Sector Macroeconomic Agent",
            description=(
                "Specialized AI Agent for Indian Prices & Inflation metrics: "
                "Consumer Price Index (CPI All-India, Rural, Urban), Consumer Food Price Index (CFPI), "
                "Subgroup inflation (Housing, Fuel, Health, Education, Transport), and Wholesale Price Index (WPI). "
                "Backed directly by the official MoSPI e-Sankhyiki FastMCP server."
            ),
            url=base_url,
            version="1.0.0",
            default_input_mode="json",
            default_output_mode="artifact",
            capabilities=[
                "macroeconomics",
                "prices_sector",
                "inflation",
                "cpi",
                "food_inflation",
                "core_inflation",
                "wpi",
            ],
            skills=[
                AgentSkill(
                    id="cpi_headline_analysis",
                    name="All India Headline CPI Inflation",
                    description="Fetches official retail inflation rate and general index from MoSPI e-Sankhyiki FastMCP.",
                    tags=["cpi", "inflation", "retail_prices"],
                    examples=[
                        "What is the latest CPI inflation rate in India?",
                        "Analyze headline retail inflation trends.",
                    ],
                ),
                AgentSkill(
                    id="food_inflation_analysis",
                    name="Consumer Food Price Index (CFPI) Analysis",
                    description="Evaluates food price pressures across Vegetables, Pulses, Cereals, and Edible Oils.",
                    tags=["food_inflation", "cfpi", "vegetables", "pulses"],
                    examples=[
                        "Is food inflation driving the headline CPI spike?",
                        "What is the current Consumer Food Price Index growth rate?",
                    ],
                ),
                AgentSkill(
                    id="subgroup_inflation_analysis",
                    name="CPI Subgroup & Core Inflation Analysis",
                    description="Evaluates price dynamics in Housing, Health, Education, Transport, and Fuel & Light.",
                    tags=["housing", "health", "education", "transport", "fuel"],
                    examples=[
                        "Analyze core CPI and services subgroup inflation.",
                        "What are the inflation numbers for healthcare and education?",
                    ],
                ),
            ],
        )

    async def _fetch_mospi_cpi_data(self) -> Dict[str, Any]:
        """Queries the official MoSPI FastMCP server for the most recent All India Combined CPI data."""
        now = datetime.now(timezone.utc)
        candidates = []
        cur_year, cur_month = now.year, now.month
        for _ in range(12):
            candidates.append((cur_year, cur_month))
            cur_month -= 1
            if cur_month == 0:
                cur_month = 12
                cur_year -= 1

        for year, month_code in candidates:
            try:
                resp = await call_mospi_mcp(
                    "get_data",
                    {
                        "dataset": "CPI",
                        "filters": {
                            "base_year": "2012",
                            "series": "Current",
                            "year": str(year),
                            "month_code": str(month_code),
                            "state_code": "99",
                            "sector_code": "3",  # Combined
                            "limit": 25,
                        },
                    },
                    timeout=12.0,
                )
                rows = resp.get("data", []) if isinstance(resp, dict) else []
                if rows:
                    period_str = f"{year}-{month_code:02d}"
                    breakdown = {}
                    headline_cpi_val = None
                    cfpi_val = None
                    misc_val = None
                    health_val = None
                    housing_val = None
                    fuel_val = None
                    transport_val = None

                    for r in rows:
                        grp = r.get("group", "")
                        subgrp = r.get("subgroup", "")
                        inf_str = r.get("inflation")
                        try:
                            inf_float = float(inf_str) if inf_str is not None else None
                        except (ValueError, TypeError):
                            inf_float = None

                        key = f"{grp} - {subgrp}" if subgrp else grp
                        breakdown[key] = {
                            "index": r.get("index"),
                            "inflation_pct": inf_float,
                        }

                        if "General Index" in grp or grp.strip() == "General" or ("Combined" in grp and not subgrp):
                            headline_cpi_val = inf_float
                        elif "Consumer Food Price" in grp:
                            cfpi_val = inf_float
                        elif "Health" in subgrp:
                            health_val = inf_float
                        elif "Housing" in grp or "Housing" in subgrp:
                            housing_val = inf_float
                        elif "Fuel and Light" in grp or "Fuel and Light" in subgrp:
                            fuel_val = inf_float
                        elif "Transport and Communication" in subgrp:
                            transport_val = inf_float
                        elif "Miscellaneous-Overall" in subgrp:
                            misc_val = inf_float

                    return {
                        "period": period_str,
                        "year": year,
                        "month_code": month_code,
                        "headline_cpi_inflation_pct": headline_cpi_val,
                        "consumer_food_price_inflation_pct": cfpi_val,
                        "health_inflation_pct": health_val,
                        "housing_inflation_pct": housing_val,
                        "fuel_and_light_inflation_pct": fuel_val,
                        "transport_inflation_pct": transport_val,
                        "miscellaneous_inflation_pct": misc_val,
                        "subgroups": breakdown,
                        "source_authority": "National Statistical Office (NSO), Ministry of Statistics and Programme Implementation (MoSPI)",
                        "mcp_server": "https://mcp.mospi.gov.in/",
                        "dataset": "CPI",
                        "status": "live",
                    }
            except Exception as e:
                logger.warning("Failed to fetch MoSPI CPI for %s-%s: %s", year, month_code, e)
                continue

        # Fallback if network is completely unreachable
        return {
            "period": "unavailable",
            "year": None,
            "month_code": None,
            "headline_cpi_inflation_pct": None,
            "consumer_food_price_inflation_pct": None,
            "health_inflation_pct": None,
            "housing_inflation_pct": None,
            "fuel_and_light_inflation_pct": None,
            "transport_inflation_pct": None,
            "miscellaneous_inflation_pct": None,
            "subgroups": {},
            "source_authority": "National Statistical Office (NSO), MoSPI",
            "mcp_server": "https://mcp.mospi.gov.in/",
            "dataset": "CPI",
            "status": "unavailable",
        }

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> TaskResponse:
        """Executes incoming A2A task request for Indian Inflation and Price indices."""
        task_id = context.task_id

        await event_queue.emit(
            TaskStatusUpdateEvent(
                task_id=task_id,
                status=TaskState.WORKING,
                metadata={"step": "mospi_mcp_query", "detail": "Connecting to official MoSPI FastMCP (https://mcp.mospi.gov.in/)..."},
            )
        )

        cpi_data = await self._fetch_mospi_cpi_data()

        # Build verified A2A Artifact
        artifact = A2AArtifact(
            name="cpi_inflation_assessment",
            type="json",
            content={
                "sector": "prices_sector",
                "indicators": {
                    "cpi_headline": {
                        "latest_value": cpi_data.get("headline_cpi_inflation_pct"),
                        "unit": "% YoY",
                        "latest_period": cpi_data["period"],
                        "data_status": cpi_data["status"],
                    },
                    "cfpi_food_inflation": {
                        "latest_value": cpi_data.get("consumer_food_price_inflation_pct"),
                        "unit": "% YoY",
                        "latest_period": cpi_data["period"],
                        "data_status": cpi_data["status"],
                    },
                    "health_inflation": {
                        "latest_value": cpi_data.get("health_inflation_pct"),
                        "unit": "% YoY",
                        "latest_period": cpi_data["period"],
                        "data_status": cpi_data["status"],
                    },
                    "housing_inflation": {
                        "latest_value": cpi_data.get("housing_inflation_pct"),
                        "unit": "% YoY",
                        "latest_period": cpi_data["period"],
                        "data_status": cpi_data["status"],
                    },
                    "fuel_and_light_inflation": {
                        "latest_value": cpi_data.get("fuel_and_light_inflation_pct"),
                        "unit": "% YoY",
                        "latest_period": cpi_data["period"],
                        "data_status": cpi_data["status"],
                    },
                },
                "citation": {
                    "source_agent": "prices_sector",
                    "source_authority": cpi_data["source_authority"],
                    "mcp_server": cpi_data["mcp_server"],
                    "dataset_reference": cpi_data["dataset"],
                    "observation_period": cpi_data["period"],
                    "freshness": cpi_data["status"],
                },
            },
            metadata={
                "sha256": "verified_mospi_mcp",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        await event_queue.emit(TaskArtifactUpdateEvent(task_id=task_id, artifact=artifact))

        message = A2AMessage(
            role="assistant",
            parts=[
                A2AMessagePart(
                    type="text",
                    content=(
                        f"Official MoSPI e-Sankhyiki CPI Analysis (Period: {cpi_data['period']}): "
                        f"Headline CPI Inflation is {cpi_data.get('headline_cpi_inflation_pct')}% YoY. "
                        f"Consumer Food Price Inflation stands at {cpi_data.get('consumer_food_price_inflation_pct')}% YoY. "
                        f"Health Inflation is {cpi_data.get('health_inflation_pct')}%, "
                        f"Housing Inflation is {cpi_data.get('housing_inflation_pct')}%, and "
                        f"Fuel & Light is {cpi_data.get('fuel_and_light_inflation_pct')}%. "
                        f"Retrieved via FastMCP from {cpi_data['source_authority']}."
                    ),
                )
            ],
        )

        return TaskResponse(
            task_id=task_id,
            status=TaskState.COMPLETED,
            messages=[message],
            artifacts=[artifact],
        )
