"""Dining MCP tool."""

from typing import Literal, Optional

from data_api.mcp.server import mcp
from data_api.mcp.tools.result_types import DiningBuildingsResult
from data_api.runtime import get_runtime


async def _find_dining(
    restaurant_name: Optional[str] = None,
    building: Optional[str] = None,
    check_open: Optional[Literal["today", "weekday", "saturday", "sunday"]] = None,
) -> DiningBuildingsResult:
    """
    Find dining options on campus.

    Args:
        restaurant_name: Search for restaurant by name.
        building: Filter by building name (e.g., '小吃部', '水木').
            A non-empty filter returns all matching restaurants per matched building.
        check_open: Filter potentially open restaurants by schedule notes: 'today',
            'weekday', 'saturday', or 'sunday'. 'today' uses the Asia/Taipei date,
            not the current opening hours.

    Returns:
        Dictionary with buildings and nested restaurants, at most 10 per building
        unless a non-empty building filter is supplied.

    Building, restaurant name, and open-status filters apply together.
    """
    service = get_runtime().dining
    _, data = await service.fuzzy_search_dining_data(
        building_name=building,
        restaurant_name=restaurant_name,
        schedule=check_open,
    )

    buildings = []
    for b in data:
        restaurants = b.get("restaurants", [])
        if restaurants:
            buildings.append(
                {
                    "building": b.get("building"),
                    "restaurants": [
                        {
                            "name": r.get("name"),
                            "phone": r.get("phone"),
                            "schedule": r.get("schedule"),
                            "note": r.get("note") if r.get("note") else None,
                        }
                        for r in (restaurants if building else restaurants[:10])
                    ],
                }
            )

    return {"buildings": buildings}


@mcp.tool(
    name="find_dining",
    title="搜尋餐廳列表",
    description="Find restaurants and dining options on campus. "
    "Use this to find where to eat, check which restaurants are open, or search for specific food. "
    "Open-status uses schedule notes, not live opening hours; today uses the Asia/Taipei date. "
    "Building, restaurant name, and open-status filters apply together. "
    "Always returns buildings with nested restaurants, at most 10 per building. "
    "Supply a non-empty building filter to list all matches in each matched building.",
)
async def find_dining(
    restaurant_name: Optional[str] = None,
    building: Optional[str] = None,
    check_open: Optional[Literal["today", "weekday", "saturday", "sunday"]] = None,
) -> dict:
    """Find dining options on campus."""
    return await _find_dining(restaurant_name, building, check_open)
