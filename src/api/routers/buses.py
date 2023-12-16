from fastapi import APIRouter, Depends, Path

from src.api import schemas
from src.api.models.buses import Buses, after_specific_time, stops

router = APIRouter()
buses = Buses()


@router.get("/main", response_model=schemas.buses.BusMainData)
def get_main():
    """
    校本部公車資訊。
    """
    buses.get_all_data()
    return buses.get_main_data()


@router.get("/nanda", response_model=schemas.buses.BusNandaData)
def get_nanda():
    """
    南大校區區間車資訊。
    """
    buses.get_all_data()
    return buses.get_nanda_data()


@router.get(
    "/info/{bus_type}/{direction}",
    response_model=list[schemas.buses.BusInfo],
)
def get_bus_schedule(
    bus_type: schemas.buses.BusType = Path(
        ..., example="main", description="車種選擇 校本部公車 或 南大區間車"
    ),
    direction: schemas.buses.BusDirection = Path(
        ..., example="up", description="上山或下山"
    ),
):
    """
    取得公車時刻表。
    """
    buses.get_all_data()
    return buses.info_data.loc[(bus_type, direction), "data"]


@router.get(
    "/schedules/{bus_type}/{day}/{direction}",
    response_model=list[schemas.buses.BusNandaSchedule | schemas.buses.BusMainSchedule],
)
def get_bus_schedule(
    bus_type: schemas.buses.BusType = Path(
        ..., example="main", description="車種選擇 校本部公車 或 南大區間車"
    ),
    day: schemas.buses.BusDay = Path(..., example="weekday", description="平日或假日"),
    direction: schemas.buses.BusDirection = Path(
        ..., example="up", description="上山或下山"
    ),
):
    """
    取得公車時刻表。
    """
    buses.get_all_data()
    return buses.raw_schedule_data.loc[(bus_type, day, direction), "data"]


####################################################################################################
# 站牌資訊及公車停靠各站時間
####################################################################################################
@router.get(
    "/stops/{stop_name}/{bus_type}/{day}/{direction}",
    response_model=list[schemas.buses.BusStopsQueryResult],
)
def get_stop_up(
    stop_name: schemas.buses.StopsName = Path(
        ..., example="北校門口", description="公車站牌名稱"
    ),
    bus_type: schemas.buses.BusType = Path(
        ..., example="main", description="車種選擇 校本部公車 或 南大區間車"
    ),
    day: schemas.buses.BusDay = Path(..., example="weekday", description="平日或假日"),
    direction: schemas.buses.BusDirection = Path(
        ..., example="up", description="上山或下山"
    ),
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得公車站牌停靠公車資訊。
    """
    buses.gen_bus_detailed_schedule_and_update_stops_data()
    return after_specific_time(
        stops[stop_name.name].stoped_bus.loc[(bus_type, day, direction), "data"],
        query.time,
        ["arrive_time"],
    )[: query.limits]


@router.get(
    "/detailed/{bus_type}/{day}/{direction}",
    response_model=list[
        schemas.buses.BusMainDetailedSchedule | schemas.buses.BusNandaDetailedSchedule
    ],
)
def get_bus_info(
    bus_type: schemas.buses.BusType = Path(
        ..., example="main", description="車種選擇 校本部公車 或 南大區間車"
    ),
    day: schemas.buses.BusDay = Path(..., example="weekday", description="平日或假日"),
    direction: schemas.buses.BusDirection = Path(
        ..., example="up", description="上山或下山"
    ),
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得詳細公車資訊，包含抵達各站時間。
    """
    buses.gen_bus_detailed_schedule_and_update_stops_data()

    return after_specific_time(
        buses.detailed_schedule_data.loc[(bus_type, day, direction), "data"],
        query.time,
        ["dep_info", "time"],
    )[: query.limits]
