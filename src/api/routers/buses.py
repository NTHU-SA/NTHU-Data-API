from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models.buses import Buses


class BusInfo(BaseModel):
    direction: str = Field(..., description="方向")
    duration: str = Field(..., description="時刻表有效期間")
    route: str = Field(..., description="路線")
    routeEN: str = Field(..., description="英文路線")


class BusSchedule(BaseModel):
    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")


class BusNandaData(BaseModel):
    toward_south_campus_info: BusInfo = Field(..., description="本部往南大區間車資訊")
    weekday_bus_schedule_toward_south_campus: list[BusSchedule] = Field(
        ..., description="本部往南大區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_south_campus: list[BusSchedule] = Field(
        ..., description="本部往南大區間車時刻表（假日）"
    )
    toward_main_campus_info: BusInfo = Field(..., description="南大往本部區間車資訊")
    weekday_bus_schedule_toward_main_campus: list[BusSchedule] = Field(
        ..., description="南大往本部區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_main_campus: list[BusSchedule] = Field(
        ..., description="南大往本部區間車時刻表（假日）"
    )


router = APIRouter()
buses = Buses()


@router.get("/nanda", response_model=BusNandaData)
async def get_nanda():
    """
    南大校區區間車資訊。
    """
    return buses.get_nanda_data()


@router.get("/nanda/information/toward_main_campus", response_model=BusInfo)
async def get_nanda_toward_main_campus_info() -> BusInfo:
    """
    南大往本部區間車資訊。
    """
    return buses.get_nanda_data()["toward_main_campus_info"]


@router.get("/nanda/information/toward_south_campus", response_model=BusInfo)
async def get_nanda_toward_south_campus_info() -> BusInfo:
    """
    本部往南大區間車資訊。
    """
    return buses.get_nanda_data()["toward_south_campus_info"]


@router.get(
    "/nanda/schedules/weekday/toward_main_campus", response_model=list[BusSchedule]
)
async def get_nanda_weekday_bus_schedule_toward_main_campus() -> list[BusSchedule]:
    """
    南大往本部區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/schedules/weekday/toward_south_campus", response_model=list[BusSchedule]
)
async def get_nanda_weekday_bus_schedule_toward_south_campus() -> list[BusSchedule]:
    """
    本部往南大區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_south_campus"]


@router.get(
    "/nanda/schedules/weekend/toward_main_campus", response_model=list[BusSchedule]
)
async def get_nanda_weekend_bus_schedule_toward_main_campus() -> list[BusSchedule]:
    """
    南大往本部區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/schedules/weekend/toward_south_campus", response_model=list[BusSchedule]
)
async def get_nanda_weekend_bus_schedule_toward_south_campus() -> list[BusSchedule]:
    """
    本部往南大區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_south_campus"]
