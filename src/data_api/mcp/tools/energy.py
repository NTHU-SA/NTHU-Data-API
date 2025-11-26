"""Energy usage MCP tool."""

from data_api.domain.energy import services as energy_services
from data_api.mcp.server import mcp


async def _get_energy_usage() -> dict:
    """
    Get real-time electricity usage for campus.

    Returns:
        Dictionary with current electricity usage by zone.
    """
    try:
        data = await energy_services.energy_service.get_realtime_electricity_usage()
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
    except Exception as e:
        return {"error": f"Failed to fetch energy data: {str(e)}"}


@mcp.tool(
    description="Get real-time campus electricity usage. "
    "Use this to check current power consumption on campus."
)
async def get_energy_usage() -> dict:
    """Get real-time electricity usage for campus."""
    return await _get_energy_usage()
