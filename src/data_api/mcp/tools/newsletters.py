"""Newsletter MCP tool."""

from typing import Optional

from data_api.domain.newsletters import services as newsletters_services
from data_api.mcp.server import mcp


async def _get_newsletters(
    search: Optional[str] = None,
) -> dict:
    """
    Get campus newsletter information.

    Args:
        search: Optional search term to filter newsletter names.

    Returns:
        Dictionary with newsletter information.
    """
    _, newsletters = await newsletters_services.newsletters_service.get_all_newsletters()

    if search:
        from thefuzz import fuzz

        newsletters = [
            n for n in newsletters if fuzz.partial_ratio(search, n.get("name", "")) >= 60
        ]

    return {
        "count": len(newsletters),
        "newsletters": [
            {
                "name": n.get("name"),
                "link": n.get("link"),
                "latest_articles": [
                    {"title": a.get("title"), "date": a.get("date")}
                    for a in n.get("articles", [])[:3]
                ],
            }
            for n in newsletters[:15]
        ],
    }


@mcp.tool(
    description="Get campus newsletter information. "
    "Use this to find electronic newsletters from various NTHU departments."
)
async def get_newsletters(
    search: Optional[str] = None,
) -> dict:
    """Get campus newsletter information."""
    return await _get_newsletters(search)
