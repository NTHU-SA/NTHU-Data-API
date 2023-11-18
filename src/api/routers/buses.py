from fastapi import APIRouter, Depends, Path

from src.api import schemas
from src.api.models.buses import Buses, after_specific_time, stops

router = APIRouter()
buses = Buses()


####################################################################################################
# 校本部公車資訊
####################################################################################################
@router.get("/main", response_model=schemas.buses.BusMainData)
async def get_main():
    """
    校本部公車資訊。
    """
    return buses.get_main_data()


@router.get("/main/info/toward_main_gate", response_model=schemas.buses.BusInfo)
async def get_tsmc_building_toward_main_gate_info() -> schemas.buses.BusInfo:
    """
    台積館往校門口公車資訊。
    """
    return buses.get_main_data()["toward_main_gate_info"]


@router.get("/main/info/toward_tsmc_building", response_model=schemas.buses.BusInfo)
async def get_main_gate_toward_tsmc_building_info() -> schemas.buses.BusInfo:
    """
    校門口往台積館公車資訊。
    """
    return buses.get_main_data()["toward_TSMC_building_info"]


@router.get(
    "/main/schedules/weekday/toward_main_gate",
    response_model=list[schemas.buses.BusMainSchedule],
)
async def get_main_weekday_bus_schedule_toward_main_gate() -> list[
    schemas.buses.BusMainSchedule
]:
    """
    台積館往校門口公車時刻表（平日）。
    """
    return buses.get_main_data()["weekday_bus_schedule_toward_main_gate"]


@router.get(
    "/main/schedules/weekday/toward_tsmc_building",
    response_model=list[schemas.buses.BusMainSchedule],
)
async def get_main_weekday_bus_schedule_toward_tsmc_building() -> list[
    schemas.buses.BusMainSchedule
]:
    """
    校門口往台積館公車時刻表（平日）。
    """
    return buses.get_main_data()["weekday_bus_schedule_toward_TSMC_building"]


@router.get(
    "/main/schedules/weekend/toward_main_gate",
    response_model=list[schemas.buses.BusMainSchedule],
)
async def get_main_weekend_bus_schedule_toward_main_gate() -> list[
    schemas.buses.BusMainSchedule
]:
    """
    台積館往校門口公車時刻表（假日）。
    """
    return buses.get_main_data()["weekend_bus_schedule_toward_main_gate"]


@router.get(
    "/main/schedules/weekend/toward_tsmc_building",
    response_model=list[schemas.buses.BusMainSchedule],
)
async def get_main_weekend_bus_schedule_toward_tsmc_building() -> list[
    schemas.buses.BusMainSchedule
]:
    """
    校門口往台積館公車時刻表（假日）。
    """
    return buses.get_main_data()["weekend_bus_schedule_toward_TSMC_building"]


####################################################################################################
# 南大校區區間車資訊
####################################################################################################
@router.get("/nanda", response_model=schemas.buses.BusNandaData)
async def get_nanda():
    """
    南大校區區間車資訊。
    """
    return buses.get_nanda_data()


@router.get("/nanda/info/toward_main_campus", response_model=schemas.buses.BusInfo)
async def get_nanda_toward_main_campus_info() -> schemas.buses.BusInfo:
    """
    南大往本部區間車資訊。
    """
    return buses.get_nanda_data()["toward_main_campus_info"]


@router.get("/nanda/info/toward_south_campus", response_model=schemas.buses.BusInfo)
async def get_nanda_toward_south_campus_info() -> schemas.buses.BusInfo:
    """
    本部往南大區間車資訊。
    """
    return buses.get_nanda_data()["toward_south_campus_info"]


@router.get(
    "/nanda/schedules/weekday/toward_main_campus",
    response_model=list[schemas.buses.BusNandaSchedule],
)
async def get_nanda_weekday_bus_schedule_toward_main_campus() -> list[
    schemas.buses.BusNandaSchedule
]:
    """
    南大往本部區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/schedules/weekday/toward_south_campus",
    response_model=list[schemas.buses.BusNandaSchedule],
)
async def get_nanda_weekday_bus_schedule_toward_south_campus() -> list[
    schemas.buses.BusNandaSchedule
]:
    """
    本部往南大區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_south_campus"]


@router.get(
    "/nanda/schedules/weekend/toward_main_campus",
    response_model=list[schemas.buses.BusNandaSchedule],
)
async def get_nanda_weekend_bus_schedule_toward_main_campus() -> list[
    schemas.buses.BusNandaSchedule
]:
    """
    南大往本部區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/schedules/weekend/toward_south_campus",
    response_model=list[schemas.buses.BusNandaSchedule],
)
async def get_nanda_weekend_bus_schedule_toward_south_campus() -> list[
    schemas.buses.BusNandaSchedule
]:
    """
    本部往南大區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_south_campus"]


####################################################################################################
# 站牌資訊及公車停靠各站時間
####################################################################################################
@router.get(
    "/stops/{stop_name}/{bus_type}/{day}/{direction}",
    response_model=list[schemas.buses.BusStopsQueryResult],
)
async def get_stop_up(
    stop_name: schemas.buses.StopsName = Path(
        ..., example="北校門口", description="公車站牌名稱"
    ),
    bus_type: schemas.buses.BusType = Path(
        ..., example="main", description="車種選擇 校本部公車 或 南大區間車"
    ),
    direction: schemas.buses.BusDirection = Path(
        ..., example="up", description="上山或下山"
    ),
    day: schemas.buses.BusDay = Path(..., example="weekday", description="平日或假日"),
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得公車站牌停靠公車資訊。
    """
    buses.get_bus_detailed_schedule_and_update_stops_data()
    return after_specific_time(
        stops[stop_name.name].stoped_bus[bus_type][direction][day],
        query.time,
        ["arrive_time"],
    )[: query.limits]


@router.get(
    "/detailed/{bus_type}/{day}/{direction}",
    response_model=list[
        schemas.buses.BusMainDetailedSchedule | schemas.buses.BusNandaDetailedSchedule
    ],
)
async def get_bus_info(
    bus_type: schemas.buses.BusType = Path(
        ..., example="main", description="車種選擇 校本部公車 或 南大區間車"
    ),
    direction: schemas.buses.BusDirection = Path(
        ..., example="up", description="上山或下山"
    ),
    day: schemas.buses.BusDay = Path(..., example="weekday", description="平日或假日"),
    query: schemas.buses.BusQuery = Depends(),
):
    """
    取得詳細公車資訊，包含抵達各站時間。
    """
    detailed_data = buses.get_bus_detailed_schedule_and_update_stops_data()

    return after_specific_time(
        detailed_data[bus_type][direction][day], query.time, ["dep_info", "time"]
    )[: query.limits]
