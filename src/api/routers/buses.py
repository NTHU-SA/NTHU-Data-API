from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response

from src.api import constant, schemas
from src.api.models.buses import Buses, after_specific_time, stops

buses = Buses()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 的生命週期管理器，用於在應用啟動時更新公車資料。"""
    global buses

    # tasks when app starts
    await buses.update_data()
    yield
    # tasks when app stops


router = APIRouter(lifespan=lifespan)


def get_current_time_state():
    """
    取得目前時間狀態 (星期別, 時間)。

    Returns:
        tuple[str, str]: 目前星期別 ('weekday' 或 'weekend') 和時間 ('HH:MM')。
    """
    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.weekday() < 5 else "weekend"
    return current_day, current_time


@router.get("/main", response_model=schemas.buses.BusMainData, name="校本部公車資訊")
async def get_main_bus_data():
    """
    取得校本部公車資訊。
    """
    await buses.update_data()
    try:
        return buses.get_main_data()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve main bus data: {e}"
        )


@router.get(
    "/nanda", response_model=schemas.buses.BusNandaData, name="南大校區區間車資訊"
)
async def get_nanda_bus_data():
    """
    取得南大校區區間車資訊。
    """
    await buses.update_data()
    try:
        return buses.get_nanda_data()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve nanda bus data: {e}"
        )


@router.get(
    "/info/{bus_type}/{direction}",
    response_model=list[schemas.buses.BusInfo],
    name="公車路線資訊",
)
async def get_bus_route_info(
    bus_type: Literal["main", "nanda"] = constant.buses.BUS_TYPE_PATH,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_PATH,
):
    """
    取得指定公車路線的資訊。

    Args:
        bus_type (Literal["main", "nanda"]): 公車類型 (校本部或南大區間車)。
        direction (schemas.buses.BusDirection): 行車方向 (up 或 down)。

    Returns:
        list[schemas.buses.BusInfo]: 公車路線資訊列表。

    Raises:
        HTTPException: 如果無法取得公車路線資訊，則拋出 500 錯誤。
    """
    await buses.update_data()
    try:
        data = buses.info_data.loc[(bus_type, direction), "data"]
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
    response_model=list[schemas.buses.BusStopsInfo],
    name="停靠站資訊",
)
async def get_bus_stops_info():
    """
    取得所有公車停靠站點的資訊。

    Returns:
        list[schemas.buses.BusStopsInfo]: 公車停靠站點資訊列表。
    """
    await buses.update_data()
    try:
        return buses.gen_bus_stops_info()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve bus stops info: {e}"
        )


@router.get(
    "/schedules/",
    response_model=list[
        schemas.buses.BusMainSchedule | schemas.buses.BusNandaSchedule | None
    ],
    name="公車時刻表",
)
async def get_bus_schedule(
    bus_type: schemas.buses.BusRouteType = constant.buses.BUS_TYPE_QUERY,
    day: schemas.buses.BusDayWithCurrent = constant.buses.BUS_DAY_QUERY,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_QUERY,
):
    """
    取得指定條件的公車時刻表。

    Args:
        bus_type (schemas.buses.BusType): 公車類型 (all, main, nanda)。
        day (schemas.buses.BusDayWithCurrent): 星期別 (all, weekday, weekend, current)。
        direction (schemas.buses.BusDirection): 行車方向 (all, up, down)。

    Returns:
        list[schemas.buses.BusMainSchedule | schemas.buses.BusNandaSchedule | None]: 公車時刻表列表。

    Raises:
        HTTPException: 如果無法取得公車時刻表，則拋出 404 或 500 錯誤。
    """
    await buses.update_data()
    try:
        if day != "current":
            schedule_data = buses.raw_schedule_data.loc[
                (bus_type, day, direction), "data"
            ]
            return schedule_data
        else:
            current_day, current_time = get_current_time_state()
            schedule_data = buses.raw_schedule_data.loc[
                (bus_type, current_day, direction), "data"
            ]
            res = after_specific_time(
                schedule_data,
                current_time,
                ["time"],
            )
            return res[: constant.buses.DEFAULT_LIMIT_DAY_CURRENT]
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
    "/stops/{stop_name}/",
    response_model=list[schemas.buses.BusStopsQueryResult | None],
    name="站點停靠公車資訊",
)
async def get_stop_bus_info(
    stop_name: schemas.buses.StopsName = constant.buses.STOPS_NAME_PATH,
    bus_type: schemas.buses.BusRouteType = constant.buses.BUS_TYPE_QUERY,
    day: schemas.buses.BusDayWithCurrent = constant.buses.BUS_DAY_QUERY,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_QUERY,
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得指定站點的公車停靠資訊。

    Args:
        stop_name (schemas.buses.StopsName): 站點名稱 (enum)。
        bus_type (schemas.buses.BusType): 公車類型 (all, main, nanda)。
        day (schemas.buses.BusDayWithCurrent): 星期別 (all, weekday, weekend, current)。
        direction (schemas.buses.BusDirection): 行車方向 (all, up, down)。
        query (schemas.buses.BusQuery): 查詢參數，包含時間和數量限制。

    Returns:
        list[schemas.buses.BusStopsQueryResult | None]: 站點停靠公車資訊列表。

    Raises:
        HTTPException: 如果無法取得站點停靠公車資訊，則拋出 404 或 500 錯誤。
    """
    await buses.update_data()
    return_limit = (
        query.limits
        if day != "current"
        else min(filter(None, (query.limits, constant.buses.DEFAULT_LIMIT_DAY_CURRENT)))
    )
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    try:
        stop_data = stops[stop_name.name].stopped_bus.loc[
            (bus_type, find_day, direction), "data"
        ]
        res = after_specific_time(
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
    "/detailed/",
    response_model=list[
        schemas.buses.BusMainDetailedSchedule
        | schemas.buses.BusNandaDetailedSchedule
        | None
    ],
    name="詳細公車時刻表",
)
async def get_bus_detailed_schedule(
    bus_type: schemas.buses.BusRouteType = constant.buses.BUS_TYPE_QUERY,
    day: schemas.buses.BusDayWithCurrent = constant.buses.BUS_DAY_QUERY,
    direction: schemas.buses.BusDirection = constant.buses.BUS_DIRECTION_QUERY,
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得詳細公車時刻表，包含抵達各站時間。

    Args:
        bus_type (schemas.buses.BusType): 公車類型 (all, main, nanda)。
        day (schemas.buses.BusDayWithCurrent): 星期別 (all, weekday, weekend, current)。
        direction (schemas.buses.BusDirection): 行車方向 (all, up, down)。
        query (schemas.buses.BusQuery): 查詢參數，包含時間和數量限制。

    Returns:
        list[schemas.buses.BusMainDetailedSchedule | schemas.buses.BusNandaDetailedSchedule | None]: 詳細公車時刻表列表。

    Raises:
        HTTPException: 如果無法取得詳細公車時刻表，則拋出 404 或 500 錯誤。
    """
    await buses.update_data()
    return_limit = (
        query.limits
        if day != "current"
        else min(filter(None, (query.limits, constant.buses.DEFAULT_LIMIT_DAY_CURRENT)))
    )
    find_day, after_time = (
        (day, query.time) if day != "current" else get_current_time_state()
    )

    try:
        detailed_schedule_data = buses.detailed_schedule_data.loc[
            (bus_type, find_day, direction), "data"
        ]
        res = after_specific_time(
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
