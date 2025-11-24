"""
Buses router.

Handles HTTP endpoints for bus-related queries.
Delegates business logic to domain services.
"""

from datetime import datetime
from typing import Literal, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Path

from data_api.api.schemas import buses as schemas
from data_api.domain.buses import services

# Constants
DEFAULT_LIMIT_DAY_CURRENT = 5

router = APIRouter()


def add_custom_header(response: Response):
    """Add X-Data-Commit-Hash header."""
    response.headers["X-Data-Commit-Hash"] = str(
        services.buses_service.last_commit_hash
    )


def get_current_time_state():
    """
    Get current time state (day type and time).
    """
    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.weekday() < 5 else "weekend"
    return current_day, current_time


@router.get(
    "/routes",
    response_model=list[schemas.BusInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusRouteData",
)
async def get_bus_route_metadata(
    bus_type: Literal["main", "nanda"] = Query(None, description="車種選擇"),
    direction: Literal["up", "down"] = Query(None, description="方向選擇"),
):
    """
    取得校園公車資訊。
    - 校本部來自[總務處事務組](https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw)
    - 南大來自[總務處事務組](https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw)
    """
    await services.buses_service.update_data()
    try:
        return services.buses_service.get_route_info(bus_type, direction)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve bus metadata: {e}"
        )


@router.get(
    "/info/stops",
    response_model=list[schemas.BusStopsInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusStopsInformation",
)
async def get_bus_stops_information():
    """取得所有公車站牌的經緯度與資訊。"""
    await services.buses_service.update_data()
    try:
        return services.buses_service.gen_bus_stops_info()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve bus stops info: {e}"
        )


@router.get(
    "/schedules",
    # 使用 Union 整合兩種回傳模型
    response_model=list[
        Union[
            schemas.BusMainDetailedSchedule,
            schemas.BusNandaDetailedSchedule,
            schemas.BusMainSchedule,
            schemas.BusNandaSchedule,
            None,
        ]
    ],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusSchedules",
    response_description="取得公車時刻表信息。",
)
async def get_bus_schedules(
    bus_type: schemas.BusRouteType = Query(..., description="車種選擇"),
    day: schemas.BusDayWithCurrent = Query(..., description="平日、假日或目前時刻"),
    direction: schemas.BusDirection = Query(..., description="上山或下山"),
    details: bool = Query(False, description="是否包含詳細站點時間資訊"),  # 新增參數
    query: schemas.BusQuery = Depends(),
):
    """
    取得指定條件的公車時刻表。
    - **details=False**: 回傳簡易時刻表（僅發車時間）。
    - **details=True**: 回傳詳細時刻表（包含每站預估到達時間）。
    """
    await services.buses_service.update_data()

    # 1. 計算要查詢的時間點與模式
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    try:
        time_path = ["dep_info", "time"] if details else ["time"]
        raw_data = services.buses_service.get_schedule(
            route_type=bus_type,
            day=find_day,
            direction=direction,
            detailed=details,
        )

        res = services.after_specific_time(
            raw_data,
            after_time or "",
            time_path,
        )

        limit = query.limits
        return res[:limit]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve bus schedule: {e}"
        )


@router.get(
    "/stops/{stop_name}",
    response_model=list[schemas.BusStopsQueryResult | None],
    dependencies=[Depends(add_custom_header)],
    operation_id="getStopBusInformationByStop",
)
async def get_stop_bus_information_by_stop(
    stop_name: schemas.BusStopsName,
    bus_type: schemas.BusRouteType = Query(..., description="車種選擇"),
    day: schemas.BusDayWithCurrent = Query(..., description="平日、假日或目前時刻"),
    direction: schemas.BusDirection = Query(..., description="上山或下山"),
    query: schemas.BusQuery = Depends(),
):
    """取得指定公車站牌的資訊和即將停靠公車。"""
    await services.buses_service.update_data()

    # Time calculation logic...
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    # Updated: Query via Service instead of Stop Instance
    raw_data = services.buses_service.get_stop_schedule(
        stop_name, bus_type, find_day, direction
    )

    if not raw_data and not services.buses_service.stops_schedule_registry:
        # Handle case where registry might be empty/error
        pass

    res = services.after_specific_time(
        raw_data,
        after_time or "",
        ["arrive_time"],
    )

    limit = query.limits
    return res[:limit]
