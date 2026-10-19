"""Bus-related MCP tools."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from data_api.domain.buses.enums import BusDayWithCurrent, BusStopsName
from data_api.domain.buses.query import resolve_bus_time
from data_api.mcp.server import mcp
from data_api.mcp.tools.result_types import BusResult
from data_api.models.buses import BusCanonicalDetailedSchedule, BusCanonicalSchedule
from data_api.runtime import get_runtime


async def _get_bus_schedule(
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
    stop: BusStopsName | None = None,
    day: BusDayWithCurrent = BusDayWithCurrent.current,
    time: str | None = None,
    details: bool = True,
) -> BusResult:
    """Query schedules using the same stop and time filters as REST."""
    service = get_runtime().buses
    await service.update_data()

    bus_time = resolve_bus_time(day, time, datetime.now())

    buses = service.query_schedule(
        route_type=route,
        day=bus_time.day,
        direction=direction,
        detailed=details,
        stop=stop,
        after_time=bus_time.after_time,
        limit=limit,
    )
    schedule_model = BusCanonicalDetailedSchedule if details else BusCanonicalSchedule
    result = {
        "current_time": bus_time.current_time,
        "day_type": bus_time.day,
        "buses": [
            schedule_model.model_validate(bus).model_dump(mode="json", exclude_none=True)
            for bus in buses
        ],
        "route_info": service.get_route_info(
            route if route != "all" else None,
            direction if direction != "all" else None,
        ),
    }
    if stop is not None:
        result["stop_name"] = stop.value
        result["stop_info"] = [
            info for info in service.gen_bus_stops_info() if info["name"] == stop.value
        ]
    return result


@mcp.tool(
    name="get_bus_schedule",
    title="查詢公車時刻表",
    description="Get campus bus schedules, optionally filtered to buses serving a specific stop. "
    "Replaces get_next_buses and get_bus_stops. "
    "With stop, time filtering uses estimated arrival time at that stop (including buses "
    "that have departed but have not arrived yet) and each bus entry includes top-level "
    "arrive_time for that stop; without stop, arrive_time is omitted and filtering uses "
    "departure time. "
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
                pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$",
                description="Time in HH:MM: arrival at the selected stop, otherwise departure",
            ),
        ]
        | None
    ) = None,
    details: bool = True,
) -> dict:
    """Get bus schedules and optional stop metadata."""
    return await _get_bus_schedule(route, direction, limit, stop, day, time, details)
