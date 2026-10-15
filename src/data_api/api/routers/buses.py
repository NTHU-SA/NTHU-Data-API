"""
Buses router.

Handles HTTP endpoints for bus-related queries.
Delegates business logic to domain services.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from data_api.api.errors import service_errors
from data_api.api.schemas import buses as schemas
from data_api.api.schemas.errors import ErrorResponse
from data_api.api.schemas.responses import SNAPSHOT_RESPONSES
from data_api.domain.buses.query import resolve_bus_time
from data_api.runtime import get_runtime

router = APIRouter(responses=SNAPSHOT_RESPONSES)


async def add_custom_header(response: Response):
    """Add X-Data-Commit-Hash header."""
    service = get_runtime().buses
    await service.update_data()
    if service.last_commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = service.last_commit_hash


def get_current_time_state():
    """
    Get current time state (day type and time).
    """
    state = resolve_bus_time("current", None, datetime.now())
    return state.day, state.after_time


def _query_bus_schedule(
    route: schemas.BusRouteType,
    day: schemas.BusDayWithCurrent,
    direction: schemas.BusDirection,
    details: bool,
    stop: schemas.BusStopsName | None,
    query: schemas.BusQuery,
):
    if day == "current":
        find_day, after_time = get_current_time_state()
    else:
        state = resolve_bus_time(day, query.time, datetime.now())
        find_day, after_time = state.day, state.after_time
    with service_errors():
        return get_runtime().buses.query_schedule(
            route_type=route,
            day=find_day,
            direction=direction,
            detailed=details,
            stop=stop,
            after_time=after_time or "",
            limit=query.limit,
        )


@router.get(
    "/routes",
    response_model=list[schemas.BusInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusRouteData",
    responses={500: {"model": ErrorResponse, "description": "Unable to retrieve bus metadata"}},
)
async def get_bus_route_metadata(
    route: Literal["main", "nanda"] = Query(None, description="路線選擇"),
    direction: Literal["up", "down"] = Query(None, description="方向選擇"),
):
    """
    取得校園公車資訊。
    - 校本部來自[總務處事務組](https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw)
    - 南大來自[總務處事務組](https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw)
    """
    with service_errors():
        return get_runtime().buses.get_route_info(route, direction)


@router.get(
    "/stops",
    response_model=list[schemas.BusStopsInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusStops",
    responses={500: {"model": ErrorResponse, "description": "Unable to retrieve bus stops"}},
)
async def get_bus_stops_information():
    """取得所有公車站牌的經緯度與資訊。"""
    with service_errors():
        return get_runtime().buses.gen_bus_stops_info()


@router.get(
    "/schedule",
    response_model=list[schemas.BusCanonicalDetailedSchedule | schemas.BusCanonicalSchedule],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusSchedule",
    responses={500: {"model": ErrorResponse, "description": "Unable to retrieve bus schedules"}},
    response_description="取得公車時刻表資訊。",
)
async def get_bus_schedule(
    route: schemas.BusRouteType = Query(schemas.BusRouteType.all, description="路線選擇"),
    day: schemas.BusDayWithCurrent = Query(
        schemas.BusDayWithCurrent.current, description="平日、假日或目前時刻"
    ),
    direction: schemas.BusDirection = Query(schemas.BusDirection.all, description="上山或下山"),
    details: bool = Query(False, description="是否包含詳細站點時間資訊"),
    stop: schemas.BusStopsName | None = Query(
        None, description="僅回傳停靠此站的班次；以此站預估到站時間篩選，包含已發車但尚未到站的班次"
    ),
    query: schemas.BusQuery = Depends(),
):
    """
    取得指定條件的公車時刻表。
    - 不指定條件時，回傳現在開始的全部路線與方向班次，預設最多 5 筆。
    - **details=False**: 回傳簡易時刻表（僅發車時間）。
    - **details=True**: 回傳詳細時刻表（包含每站預估到達時間）。
    - **stop**: 以指定站牌的預估到站時間篩選，包含已發車但尚未到站的班次；未指定時以發車時間篩選。
    """
    return _query_bus_schedule(route, day, direction, details, stop, query)
