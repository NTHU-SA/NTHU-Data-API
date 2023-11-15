from fastapi import APIRouter

from src.api import schemas
from src.api.models.buses import Buses

router = APIRouter()
buses = Buses()


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
    台積館往校門口公車時刻表（平日）
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
