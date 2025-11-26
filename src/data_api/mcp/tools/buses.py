"""Bus-related MCP tools."""

from datetime import datetime
from typing import Literal

from data_api.domain.buses import services as buses_services
from data_api.domain.buses.enums import BusStopsName
from data_api.mcp.server import mcp


async def _get_next_buses(
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
) -> dict:
    """
    Get upcoming bus departures for campus routes.

    Args:
        route: Bus route type - 'main' for main campus loop, 'nanda' for Nanda shuttle, 'all' for both.
        direction: Direction - 'up' (toward TSMC Building/Nanda), 'down' (toward Main Gate/Main Campus), 'all' for both.
        limit: Maximum number of buses to return (default 5).

    Returns:
        Dictionary with upcoming bus schedules and route information.
    """
    await buses_services.buses_service.update_data()

    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.weekday() < 5 else "weekend"

    # Get detailed schedules
    raw_data = buses_services.buses_service.get_schedule(
        route_type=route,
        day=current_day,
        direction=direction,
        detailed=True,
    )

    # Filter to buses after current time
    filtered = buses_services.after_specific_time(
        raw_data,
        current_time,
        ["dep_info", "time"],
    )

    # Format response
    buses = []
    for bus in filtered[:limit]:
        dep_info = bus.get("dep_info", {})
        buses.append(
            {
                "departure_time": dep_info.get("time"),
                "departure_stop": dep_info.get("dep_stop"),
                "description": dep_info.get("description"),
                "bus_type": bus.get("bus_type"),
                "stops": bus.get("stops_time", []),
            }
        )

    return {
        "current_time": current_time,
        "day_type": current_day,
        "buses": buses,
        "route_info": buses_services.buses_service.get_route_info(
            route if route != "all" else None,
            direction if direction != "all" else None,
        ),
    }


async def _get_bus_stops(
    stop_name: BusStopsName | str,
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
) -> dict:
    """
    Get bus stop information and upcoming buses.

    Args:
        stop_name: Specific stop to query.
        route: Bus route type filter - 'main', 'nanda', or 'all'.
        direction: Direction filter - 'up', 'down', or 'all'.
        limit: Maximum number of upcoming buses to return per stop (default 5).

    Returns:
        Dictionary with query bus stop details and upcoming bus schedules.
    """
    await buses_services.buses_service.update_data()
    stops = buses_services.buses_service.gen_bus_stops_info()

    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.weekday() < 5 else "weekend"

    result = {}

    all_stops = {
        "stops": [
            {
                "name": s.get("name"),
                "name_en": s.get("name_en"),
                "latitude": s.get("latitude"),
                "longitude": s.get("longitude"),
            }
            for s in stops
        ]
    }

    if not isinstance(stop_name, BusStopsName):
        stop_name = BusStopsName(stop_name)

    stop_name_str = stop_name.value

    result["stop_info"] = [s for s in all_stops["stops"] if s["name"] == stop_name_str]

    # Get schedule for the specific stop
    raw_data = buses_services.buses_service.get_stop_schedule(
        stop_name_str, route, current_day, direction
    )

    # Filter to buses after current time
    filtered = buses_services.after_specific_time(
        raw_data,
        current_time,
        ["arrive_time"],
    )

    result["stop_name"] = stop_name_str
    result["current_time"] = current_time
    result["day_type"] = current_day
    result["upcoming_buses"] = [
        {
            "arrive_time": bus.get("arrive_time"),
            "departure_time": bus.get("dep_time"),
            "departure_stop": bus.get("dep_stop"),
            "description": bus.get("description"),
            "bus_type": bus.get("bus_type"),
        }
        for bus in filtered[:limit]
    ]

    return result


@mcp.tool(
    description="Get the next available campus buses. "
    "Use this when someone asks about bus schedules, when the next bus is, or how to get around campus."
    "- If they are going TO Nanda Campus, query the 'up' schedule."
    "- If they are going TO Main Campus, query the 'down' schedule."
    "- Warning: If they take the bus TO Nanda (`up`), they cannot get off at other stops inside the Main Campus."
    "- Warning: If they take the bus TO Main Campus (`down`), they cannot get on the bus at stops inside the Main Campus."
)
async def get_next_buses(
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
) -> dict:
    """Get upcoming bus departures for campus routes."""
    return await _get_next_buses(route, direction, limit)


@mcp.tool(
    description="Get information about bus stops on campus, including upcoming buses for a specific stop. "
    "Use this to find bus stop locations, or to check when the next bus arrives at a specific stop. "
    "Available stops: 北校門口, 綜二館, 楓林小徑, 人社院&生科館, 台積館, 奕園停車場, 教育學院大樓&南門停車場, 南大校區校門口右側(食品路校牆邊)"
)
async def get_bus_stops(
    stop_name: BusStopsName,
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
) -> dict:
    """Get bus stop locations and upcoming buses for a specific stop."""
    return await _get_bus_stops(stop_name, route, direction, limit)
