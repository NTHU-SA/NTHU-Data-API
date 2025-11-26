"""Dining MCP tool."""

from typing import Literal, Optional

from data_api.domain.dining import services as dining_services
from data_api.mcp.server import mcp


async def _find_dining(
    restaurant_name: Optional[str] = None,
    building: Optional[str] = None,
    check_open: Literal["today", "weekday", "saturday", "sunday"] = None,
) -> dict:
    """
    Find dining options on campus.

    Args:
        restaurant_name: Search for restaurant by name.
        building: Filter by building name (e.g., '小吃部', '水木').
        check_open: Check which restaurants are open - 'today', 'weekday', 'saturday', or 'sunday'.

    Returns:
        Dictionary with restaurant information.
    """
    if check_open:
        _, restaurants = await dining_services.dining_service.get_open_restaurants(
            schedule=check_open
        )
        return {
            "schedule": check_open,
            "open_restaurants": [
                {
                    "name": r.get("name"),
                    "area": r.get("area"),
                    "phone": r.get("phone"),
                    "schedule": r.get("schedule"),
                }
                for r in restaurants[:20]
            ],
        }
    else:
        _, data = await dining_services.dining_service.fuzzy_search_dining_data(
            building_name=building,
            restaurant_name=restaurant_name,
        )

        # Format response
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
                            for r in restaurants[:10]
                        ],
                    }
                )

        return {
            "buildings": buildings,
        }


@mcp.tool(
    description="Find restaurants and dining options on campus. "
    "Use this to find where to eat, check which restaurants are open, or search for specific food."
)
async def find_dining(
    restaurant_name: Optional[str] = None,
    building: Optional[str] = None,
    check_open: Literal["today", "weekday", "saturday", "sunday"] = None,
) -> dict:
    """Find dining options on campus."""
    return await _find_dining(restaurant_name, building, check_open)
