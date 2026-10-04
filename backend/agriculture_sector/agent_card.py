"""Agriculture A2A discovery using the shared AgentCard contract."""
from __future__ import annotations

from core.protocols.a2a.models import AgentCard, AgentSkill
from .models import AgricultureFinding, AgricultureQuery

CAPABILITIES = {
    "crop_production": "Crop production analysis", "crop_yield": "Crop yield analysis",
    "mandi_price": "Mandi price analysis", "agricultural_market": "Agricultural market analysis",
    "msp": "MSP analysis", "rainfall_monsoon": "Rainfall and monsoon analysis",
    "agricultural_input": "Agricultural input analysis", "agriculture_policy": "Agriculture policy/data analysis",
    "agriculture_supply": "Agriculture supply-side diagnosis",
}


def get_agent_card(base_url: str = "http://localhost:8000/agriculture-sector") -> AgentCard:
    return AgentCard(
        name="Agriculture Agent", url=base_url,
        description=(
            "Indian Agriculture: crops, mandi prices, arrivals, MSP, rainfall, inputs and policy. "
            "MCP sources: Agmarknet; MoSPI eSankhyiki; weather_mcp (IMD preferred, "
            "Open-Meteo identified when used); Data.gov.in. "
            "A2A collaboration partners: Prices Agent, Real Sector Agent, External Sector Agent, Fiscal Agent. "
            "Shares cited findings; does not own CPI, WPI, GDP/GVA, bank credit or equities."
        ),
        capabilities=["agriculture", *CAPABILITIES],
        skills=[AgentSkill(
            id=f"agriculture_{key}_analysis", name=name, description=name,
            tags=["agriculture", *key.split("_")],
            input_schema=AgricultureQuery.model_json_schema(),
            output_schema=AgricultureFinding.model_json_schema(),
        ) for key, name in CAPABILITIES.items()],
    )
