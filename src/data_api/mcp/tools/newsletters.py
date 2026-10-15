"""Newsletter MCP tool."""

from typing import Optional

from data_api.mcp.server import mcp
from data_api.mcp.tools.result_types import NewslettersResult
from data_api.runtime import get_runtime


async def _get_newsletters(
    search: Optional[str] = None,
) -> NewslettersResult:
    """
    Get campus newsletter information.

    Args:
        search: Optional search term to filter newsletter names.

    Returns:
        Dictionary with newsletter information.
    """
    _, newsletters = await get_runtime().newsletters.get_newsletters(name=search)

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
            for n in newsletters
        ],
    }


@mcp.tool(
    name="get_newsletters",
    title="搜尋電子報列表",
    description="Get campus newsletter information. "
    "Use this to find electronic newsletters from various NTHU departments.",
)
async def get_newsletters(
    search: Optional[str] = None,
) -> dict:
    """Get campus newsletter information."""
    return await _get_newsletters(search)
