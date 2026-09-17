from fastmcp import FastMCP
from .clients.agri_data_client import AgricultureDataClient
mcp_server=FastMCP("agriculture_sector_mcp"); _client=AgricultureDataClient()
@mcp_server.tool(name="get_foodgrain_production_snapshot")
def get_foodgrain_production_snapshot(): return _client.get_foodgrain_production()
@mcp_server.tool(name="get_msp_growth_snapshot")
def get_msp_growth_snapshot(): return _client.get_msp_growth()
