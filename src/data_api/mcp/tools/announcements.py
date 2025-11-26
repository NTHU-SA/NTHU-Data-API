"""Announcements MCP tool."""

from typing import Optional

from data_api.domain.announcements import services as announcements_services
from data_api.mcp.server import mcp


async def _get_announcements(
    department: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    Get campus announcements.

    Args:
        department: Filter by department name (fuzzy match).
        keyword: Search in announcement titles.
        limit: Maximum number of announcements per department (default 10).

    Returns:
        Dictionary with announcements grouped by department.
    """
    _, data = await announcements_services.announcements_service.fuzzy_search_announcements(
        department=department,
        title=keyword,
    )

    # Format response - limit articles per department
    result = []
    for source in data[:10]:  # Limit departments
        articles = source.get("articles", [])[:limit]
        if articles:
            result.append(
                {
                    "department": source.get("department"),
                    "language": source.get("language"),
                    "articles": [
                        {
                            "title": a.get("title"),
                            "link": a.get("link"),
                            "date": a.get("date"),
                        }
                        for a in articles
                    ],
                }
            )

    return {
        "count": sum(len(d["articles"]) for d in result),
        "sources": result,
    }


@mcp.tool(
    description="Get campus announcements from NTHU departments. "
    "Use this to find news, notices, or updates from campus offices."
)
async def get_announcements(
    department: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Get campus announcements."""
    return await _get_announcements(department, keyword, limit)
