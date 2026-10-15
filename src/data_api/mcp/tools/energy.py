"""Energy usage MCP tool."""

from data_api.mcp.errors import live_tool_errors
from data_api.mcp.server import mcp
from data_api.mcp.tools.result_types import EnergyResult
from data_api.runtime import get_runtime


async def _get_energy_usage() -> EnergyResult:
    """
    Get real-time electricity usage for campus.

    Returns:
        Dictionary with current electricity usage by zone.
    """
    with live_tool_errors():
        data = await get_runtime().energy.get_realtime_electricity_usage()
        zones = []
        for item in data:
            capacity = item.get("capacity") or 1  # Avoid division by zero
            usage = item.get("data", 0)
            zones.append(
                {
                    "name": item.get("name"),
                    "usage_kw": usage,
                    "capacity_kw": item.get("capacity"),
                    "usage_percent": round(usage / capacity * 100, 1) if capacity > 0 else 0,
                    "last_updated": item.get("last_updated"),
                }
            )
        return {"zones": zones}


@mcp.tool(
    name="get_energy_usage",
    title="查詢校園即時用電",
    description="Get real-time campus electricity usage. "
    "Use this to check current power consumption on campus.",
)
async def get_energy_usage() -> dict:
    """Get real-time electricity usage for campus."""
    return await _get_energy_usage()
