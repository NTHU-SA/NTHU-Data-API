"""
Buses router.

Handles HTTP endpoints for bus-related queries.
Delegates business logic to domain services.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

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

    Returns:
        tuple[str, str]: Current day type ('weekday' or 'weekend') and time ('HH:MM').
    """
    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.weekday() < 5 else "weekend"
    return current_day, current_time


@router.get(
    "/main",
    response_model=schemas.BusMainData,
    dependencies=[Depends(add_custom_header)],
    operation_id="getMainCampusBusData",
)
async def get_main_campus_bus_data():
    """
    取得校本部公車資訊。
    來自[總務處事務組](https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw)
    """
    await services.buses_service.update_data()
    try:
        return services.buses_service.get_main_data()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve main bus data: {e}"
        )


@router.get(
    "/nanda",
    response_model=schemas.BusNandaData,
    dependencies=[Depends(add_custom_header)],
    operation_id="getNandaCampusBusData",
)
async def get_nanda_campus_bus_data():
    """
    取得南大校區區間車資訊。
    來自[總務處事務組](https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw)
    """
    await services.buses_service.update_data()
    try:
        return services.buses_service.get_nanda_data()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve nanda bus data: {e}"
        )


@router.get(
    "/info/{bus_type}/{direction}",
    response_model=list[schemas.BusInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusRouteInformation",
)
async def get_bus_route_information(
    bus_type: Literal["main", "nanda"],
    direction: schemas.BusDirection,
):
    """取得指定公車路線的資訊。"""
    await services.buses_service.update_data()
    try:
        data = services.buses_service.info_data.loc[(bus_type, direction), "data"]
        return data
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Bus info not found for type '{bus_type}' and direction '{direction}'.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve bus info: {e}",
        )


@router.get(
    "/info/stops",
    response_model=list[schemas.BusStopsInfo],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusStopsInformation",
)
async def get_bus_stops_information():
    """取得所有公車站牌的資訊。"""
    await services.buses_service.update_data()
    try:
        return services.buses_service.gen_bus_stops_info()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve bus stops info: {e}"
        )


@router.get(
    "/schedules",
    response_model=list[schemas.BusMainSchedule | schemas.BusNandaSchedule | None],
    dependencies=[Depends(add_custom_header)],
    operation_id="getBusSchedules",
)
async def get_bus_schedules(
    bus_type: schemas.BusRouteType = Query(..., example="main", description="車種選擇"),
    day: schemas.BusDayWithCurrent = Query(
        ..., example="weekday", description="平日、假日或目前時刻"
    ),
    direction: schemas.BusDirection = Query(
        ..., example="up", description="上山或下山"
    ),
):
    """取得指定條件的公車時刻表。"""
    await services.buses_service.update_data()
    try:
        if day != "current":
            schedule_data = services.buses_service.raw_schedule_data.loc[
                (bus_type, day, direction), "data"
            ]
            return schedule_data
        else:
            current_day, current_time = get_current_time_state()
            schedule_data = services.buses_service.raw_schedule_data.loc[
                (bus_type, current_day, direction), "data"
            ]
            res = services.after_specific_time(
                schedule_data,
                current_time,
                ["time"],
            )
            return res[:DEFAULT_LIMIT_DAY_CURRENT]
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Schedule not found for type '{bus_type}', day '{day}', and direction '{direction}'.",
        )
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
    bus_type: schemas.BusRouteType = Query(..., example="main"),
    day: schemas.BusDayWithCurrent = Query(..., example="weekday"),
    direction: schemas.BusDirection = Query(..., example="up"),
    query: schemas.BusQuery = Depends(),
):
    """取得指定公車站牌的資訊和即將停靠公車。"""
    await services.buses_service.update_data()
    return_limit = (
        query.limits
        if day != "current"
        else min(filter(None, (query.limits, DEFAULT_LIMIT_DAY_CURRENT)))
    )
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    try:
        stop_data = services.stops[stop_name.name].stopped_bus_data[
            (bus_type, find_day, direction)
        ]
        res = services.after_specific_time(
            stop_data,
            after_time,
            ["arrive_time"],
        )
        return res[:return_limit]

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"""No bus stop data found for stop '{stop_name}', type '{bus_type}', day '{day}', \
            and direction '{direction}'.""",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stop bus info: {e}",
        )


@router.get(
    "/detailed",
    response_model=list[
        schemas.BusMainDetailedSchedule | schemas.BusNandaDetailedSchedule | None
    ],
    dependencies=[Depends(add_custom_header)],
    operation_id="getDetailedBusSchedule",
)
async def get_detailed_bus_schedule(
    bus_type: schemas.BusRouteType = Query(..., example="main"),
    day: schemas.BusDayWithCurrent = Query(..., example="weekday"),
    direction: schemas.BusDirection = Query(..., example="up"),
    query: schemas.BusQuery = Depends(),
):
    """取得詳細的公車時刻表，包括每個站點的到達時間。"""
    await services.buses_service.update_data()
    return_limit = (
        query.limits
        if day != "current"
        else min(filter(None, (query.limits, DEFAULT_LIMIT_DAY_CURRENT)))
    )
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    try:
        detailed_schedule_data = services.buses_service.detailed_schedule_data.loc[
            (bus_type, find_day, direction), "data"
        ]
        res = services.after_specific_time(
            detailed_schedule_data,
            after_time,
            ["dep_info", "time"],
        )
        return res[:return_limit]
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Detailed schedule not found for type '{bus_type}', day '{day}', and direction '{direction}'.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve detailed bus schedule: {e}",
        )
