from fastapi import APIRouter

from ..models.buses import Buses
from src.api import schemas


router = APIRouter()
buses = Buses()


@router.get("/nanda", response_model=schemas.buses.BusNandaData)
async def get_nanda():
    """
    南大校區區間車資訊。
    """
    return buses.get_nanda_data()


@router.get(
    "/nanda/information/toward_main_campus", response_model=schemas.buses.BusInfo
)
async def get_nanda_toward_main_campus_info() -> schemas.buses.BusInfo:
    """
    南大往本部區間車資訊。
    """
    return buses.get_nanda_data()["toward_main_campus_info"]


@router.get(
    "/nanda/information/toward_south_campus", response_model=schemas.buses.BusInfo
)
async def get_nanda_toward_south_campus_info() -> schemas.buses.BusInfo:
    """
    本部往南大區間車資訊。
    """
    return buses.get_nanda_data()["toward_south_campus_info"]


@router.get(
    "/nanda/schedules/weekday/toward_main_campus",
    response_model=list[schemas.buses.BusSchedule],
)
async def get_nanda_weekday_bus_schedule_toward_main_campus() -> list[
    schemas.buses.BusSchedule
]:
    """
    南大往本部區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/schedules/weekday/toward_south_campus",
    response_model=list[schemas.buses.BusSchedule],
)
async def get_nanda_weekday_bus_schedule_toward_south_campus() -> list[
    schemas.buses.BusSchedule
]:
    """
    本部往南大區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_south_campus"]


@router.get(
    "/nanda/schedules/weekend/toward_main_campus",
    response_model=list[schemas.buses.BusSchedule],
)
async def get_nanda_weekend_bus_schedule_toward_main_campus() -> list[
    schemas.buses.BusSchedule
]:
    """
    南大往本部區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/schedules/weekend/toward_south_campus",
    response_model=list[schemas.buses.BusSchedule],
)
async def get_nanda_weekend_bus_schedule_toward_south_campus() -> list[
    schemas.buses.BusSchedule
]:
    """
    本部往南大區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_south_campus"]
