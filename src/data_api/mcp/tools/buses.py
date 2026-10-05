"""Bus-related MCP tools."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from data_api.api.schemas.buses import BusCanonicalDetailedSchedule, BusCanonicalSchedule
from data_api.domain.buses import services as buses_services
from data_api.domain.buses.enums import BusDayWithCurrent, BusStopsName
from data_api.mcp.server import mcp


async def _get_bus_schedule(
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
    stop: BusStopsName | None = None,
    day: BusDayWithCurrent = BusDayWithCurrent.current,
    time: str | None = None,
    details: bool = True,
) -> dict:
    """Query schedules using the same stop and departure-time filters as REST."""
    await buses_services.buses_service.update_data()

    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    find_day = ("weekday" if current.weekday() < 5 else "weekend") if day == "current" else day
    after_time = current_time if day == "current" else time or ""

    buses = buses_services.buses_service.query_schedule(
        route_type=route,
        day=find_day,
        direction=direction,
        detailed=details,
        stop=stop,
        after_time=after_time,
        limit=limit,
    )
    schedule_model = BusCanonicalDetailedSchedule if details else BusCanonicalSchedule
    result = {
        "current_time": current_time,
        "day_type": find_day,
        "buses": [schedule_model.model_validate(bus).model_dump(mode="json") for bus in buses],
        "route_info": buses_services.buses_service.get_route_info(
            route if route != "all" else None,
            direction if direction != "all" else None,
        ),
    }
    if stop is not None:
        result["stop_name"] = stop.value
        result["stop_info"] = [
            info
            for info in buses_services.buses_service.gen_bus_stops_info()
            if info["name"] == stop.value
        ]
    return result


@mcp.tool(
    name="get_bus_schedule",
    title="查詢公車時刻表",
    description="Get campus bus schedules, optionally filtered to buses serving a specific stop. "
    "Replaces get_next_buses and get_bus_stops. "
    "All time filtering uses departure time, not arrival time at the selected stop. "
    "Use details=true for departure information and arrival times at all stops; "
    "details=false returns simple departure schedules. "
    "Line identifiers are main_red, main_green, nanda_route_1, and nanda_route_2. "
    "day=current uses the current day and time and ignores time. "
    "For a selected stop, stop_info includes its location. "
    "If going TO Nanda Campus, query direction=up; TO Main Campus, direction=down. "
    "Passengers TO Nanda cannot get off at other stops inside Main Campus; "
    "passengers TO Main Campus cannot board at stops inside Main Campus.",
)
async def get_bus_schedule(
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: Annotated[int, Field(ge=1)] = 5,
    stop: BusStopsName | None = None,
    day: BusDayWithCurrent = BusDayWithCurrent.current,
    time: (
        Annotated[
            str,
            Field(
                pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$", description="Departure time in HH:MM"
            ),
        ]
        | None
    ) = None,
    details: bool = True,
) -> dict:
    """Get bus schedules and optional stop metadata."""
    return await _get_bus_schedule(route, direction, limit, stop, day, time, details)
