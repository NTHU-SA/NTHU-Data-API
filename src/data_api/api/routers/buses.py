"""
Buses router.

Handles HTTP endpoints for bus-related queries.
Delegates business logic to domain services.
"""

from datetime import datetime
from typing import Literal, Union

from fastapi import APIRouter, Depends, Query, Response

from data_api.api.errors import service_errors
from data_api.api.schemas import buses as schemas
from data_api.api.schemas.errors import ErrorResponse
from data_api.domain.buses import services

# Constants
DEFAULT_LIMIT_DAY_CURRENT = 5

router = APIRouter()


async def add_custom_header(response: Response):
    """Add X-Data-Commit-Hash header."""
    await services.buses_service.update_data()
    if services.buses_service.last_commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = services.buses_service.last_commit_hash


def get_current_time_state():
    """
    Get current time state (day type and time).
    """
    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.weekday() < 5 else "weekend"
    return current_day, current_time


def _query_bus_schedule(
    route: schemas.BusRouteType,
    day: schemas.BusDayWithCurrent,
    direction: schemas.BusDirection,
    details: bool,
    stop: schemas.BusStopsName | None,
    query: schemas.BusQuery,
):
    find_day, after_time = (day, query.time) if day != "current" else get_current_time_state()
    with service_errors():
        return services.buses_service.query_schedule(
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
        return services.buses_service.get_route_info(route, direction)


@router.get(
    "/stops",
    response_model=list[schemas.BusStopsInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusStops",
    responses={500: {"model": ErrorResponse, "description": "Unable to retrieve bus stops"}},
)
@router.get(
    "/info/stops",
    response_model=list[schemas.BusStopsInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusStopsInformation",
    deprecated=True,
    description="已棄用，將於下一個 major 版本移除。請改用 GET /buses/stops，回應格式不變。",
    responses={500: {"model": ErrorResponse, "description": "Unable to retrieve bus stops"}},
)
async def get_bus_stops_information():
    """取得所有公車站牌的經緯度與資訊。"""
    with service_errors():
        return services.buses_service.gen_bus_stops_info()


@router.get(
    "/schedules",
    response_model=list[Union[schemas.BusDetailedSchedule, schemas.BusSchedule, None]],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusSchedules",
    responses={500: {"model": ErrorResponse, "description": "Unable to retrieve bus schedules"}},
    response_description="取得公車時刻表信息。",
    deprecated=True,
    description=(
        "已棄用，將於下一個 major 版本移除。請改用 GET /buses/schedule，並將 bus_type 改為 route。"
        "新版預設 route=all、day=current、direction=all，亦支援 stop 篩選。"
    ),
)
async def get_bus_schedules(
    bus_type: schemas.BusRouteType = Query(..., description="車種選擇"),
    day: schemas.BusDayWithCurrent = Query(..., description="平日、假日或目前時刻"),
    direction: schemas.BusDirection = Query(..., description="上山或下山"),
    details: bool = Query(False, description="是否包含詳細站點時間資訊"),
    stop: schemas.BusStopsName | None = Query(
        None, description="僅回傳停靠此站的班次；不影響回應格式，時間仍以發車時間篩選"
    ),
    query: schemas.BusQuery = Depends(),
):
    """取得指定條件的公車時刻表，保留舊版必填參數與回應格式。"""
    return _query_bus_schedule(bus_type, day, direction, details, stop, query)


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
        None, description="僅回傳停靠此站的班次；不影響回應格式，時間仍以發車時間篩選"
    ),
    query: schemas.BusQuery = Depends(),
):
    """
    取得指定條件的公車時刻表。
    - 不指定條件時，回傳現在開始的全部路線與方向班次，預設最多 5 筆。
    - **details=False**: 回傳簡易時刻表（僅發車時間）。
    - **details=True**: 回傳詳細時刻表（包含每站預估到達時間）。
    - **stop**: 僅篩選會停靠指定站牌的班次；time 與 current 仍以發車時間篩選。
    """
    return _query_bus_schedule(route, day, direction, details, stop, query)


@router.get(
    "/stops/{stop_name}",
    response_model=list[schemas.BusStopsQueryResult | None],
    dependencies=[Depends(add_custom_header)],
    operation_id="getStopBusInformationByStop",
    deprecated=True,
    description=(
        "已棄用，將於下一個 major 版本移除。請改用 GET /buses/schedule?stop={stop_name}&details=true。"
        "新 API 回傳時刻表格式，並以發車時間篩選；此舊 API 保留到站資訊與到站時間篩選。"
    ),
    responses={500: {"model": ErrorResponse, "description": "Unable to retrieve bus schedules"}},
)
async def get_stop_bus_information_by_stop(
    stop_name: schemas.BusStopsName,
    bus_type: schemas.BusRouteType = Query(..., description="車種選擇"),
    day: schemas.BusDayWithCurrent = Query(..., description="平日、假日或目前時刻"),
    direction: schemas.BusDirection = Query(..., description="上山或下山"),
    query: schemas.BusQuery = Depends(),
):
    """取得指定公車站牌的資訊和即將停靠公車。"""
    find_day, after_time = (day, query.time) if day != "current" else get_current_time_state()

    with service_errors():
        raw_data = services.buses_service.get_stop_schedule(
            stop_name, bus_type, find_day, direction
        )
        res = services.after_specific_time(raw_data, after_time or "", ["arrive_time"])
        return res[: query.limit]
