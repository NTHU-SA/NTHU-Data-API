"""Library information MCP tool."""

from typing import Literal

from pydantic import validate_call

from data_api.domain.libraries.services import libraries_service
from data_api.mcp.errors import live_tool_errors
from data_api.mcp.server import mcp


@validate_call
async def _get_library_info(
    info_type: Literal["space", "lost_and_found"] = "space",
) -> dict:
    """
    Get library information.

    Args:
        info_type: Type of information - 'space' for study space availability, 'lost_and_found' for lost items.

    Returns:
        Dictionary with library information.
    """
    with live_tool_errors():
        if info_type == "space":
            spaces = await libraries_service.get_space_availability()
            return {
                "spaces": [
                    {
                        "zone": s.get("zonename"),
                        "type": s.get("spacetypename"),
                        "available": s.get("count"),
                    }
                    for s in spaces
                ]
            }
        items = await libraries_service.get_lost_and_found_items()
        return {"items": items[:10]}


@mcp.tool(
    name="get_library_info",
    title="查詢圖書館資訊",
    description="Get library information including space availability and lost items. "
    "Use this to check if study spaces are available or to find lost items.",
)
async def get_library_info(
    info_type: Literal["space", "lost_and_found"] = "space",
) -> dict:
    """Get library information."""
    return await _get_library_info(info_type)
