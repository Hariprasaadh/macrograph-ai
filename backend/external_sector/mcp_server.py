from fastmcp import FastMCP
from .clients.external_data_client import ExternalDataClient
mcp_server=FastMCP("external_sector_mcp"); _client=ExternalDataClient()
@mcp_server.tool(name="get_forex_reserves_snapshot")
def get_forex_reserves_snapshot(): return _client.get_forex_reserves()
@mcp_server.tool(name="get_exchange_rate_snapshot")
def get_exchange_rate_snapshot(): return _client.get_exchange_rate()
@mcp_server.tool(name="get_trade_balance_snapshot")
def get_trade_balance_snapshot(): return _client.get_trade_balance()
