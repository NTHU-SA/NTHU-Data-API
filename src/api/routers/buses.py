from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models.buses import Buses


class Info(BaseModel):
    direction: str = Field(..., description="方向")
    duration: str = Field(..., description="時刻表有效期間")
    route: str = Field(..., description="路線")
    routeEN: str = Field(..., description="英文路線")


class Schedule(BaseModel):
    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")


class NandaData(BaseModel):
    toward_south_campus_info: Info = Field(..., description="本部往南大區間車資訊")
    weekday_bus_schedule_toward_south_campus: list[Schedule] = Field(
        ..., description="本部往南大區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_south_campus: list[Schedule] = Field(
        ..., description="本部往南大區間車時刻表（假日）"
    )
    toward_main_campus_info: Info = Field(..., description="南大往本部區間車資訊")
    weekday_bus_schedule_toward_main_campus: list[Schedule] = Field(
        ..., description="南大往本部區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_main_campus: list[Schedule] = Field(
        ..., description="南大往本部區間車時刻表（假日）"
    )


router = APIRouter(
    prefix="/buses",
    tags=["buses"],
    responses={404: {"description": "Not found"}},
)

buses = Buses()


@router.get(
    "/nanda",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "toward_south_campus_info": {},
                        "weekday_bus_schedule_toward_south_campus": {},
                        "weekend_bus_schedule_toward_south_campus": {},
                        "toward_main_campus_info": {},
                        "weekday_bus_schedule_toward_main_campus": {},
                        "weekend_bus_schedule_toward_main_campus": {},
                    }
                },
            },
        },
    },
    response_model=NandaData,
)
async def get_nanda():
    """
    南大校區區間車資訊。
    """
    return buses.get_nanda_data()


@router.get(
    "/nanda/toward_south_campus_info",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "direction": "往南大校區 (To Nanda Campus)",
                        "duration": "2023/10/16 ~ 2023/11/12",
                        "route": "北校門口 → 綜二館 → 人社院/生科館 → 台積館(經寶山路) → 南大校區校門口右側(食品路校牆邊)",
                        "routeEN": "School North Gate → General Building II → CHSS/CLS Building → TSMC Building(Baoshan Rd.) → The right side of NandaCampus front gate(Shipin Road)",
                    }
                },
            },
        },
    },
    response_model=Info,
)
async def get_nanda_toward_south_campus_info():
    """
    本部往南大區間車資訊。
    """
    return buses.get_nanda_data()["toward_south_campus_info"]


@router.get(
    "/nanda/weekday_bus_schedule_toward_south_campus",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {"time": "7:30", "description": "此為付費市區公車(83號公車直達兩校區)"},
                        {"time": "7:40", "description": ""},
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[Schedule],
)
async def get_nanda_weekday_bus_schedule_toward_south_campus():
    """
    本部往南大區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_south_campus"]


@router.get(
    "/nanda/weekend_bus_schedule_toward_south_campus",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {"time": "8:30", "description": ""},
                        {"time": "12:30", "description": ""},
                        {"time": "14:30", "description": ""},
                        {"time": "17:30", "description": ""},
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[Schedule],
)
async def get_nanda_weekend_bus_schedule_toward_south_campus():
    """
    本部往南大區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_south_campus"]


@router.get(
    "/nanda/toward_main_campus_info",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "direction": "往校本部 (To Main Campus)",
                        "duration": "2023/10/16 ~ 2023/11/12",
                        "route": "南大校區校門口右側(食品路校牆邊) → 台積館(經寶山路) → 人社院/生科館 → 綜二館 → 北校門口",
                        "routeEN": "The right side of NandaCampus front gate(Shipin Road) → TSMC Building(Baoshan Rd.) → CHSS/CLS Builing → General Building II→School North Gate",
                    }
                },
            },
        },
    },
    response_model=Info,
)
async def get_nanda_toward_main_campus_info():
    """
    南大往本部區間車資訊。
    """
    return buses.get_nanda_data()["toward_main_campus_info"]


@router.get(
    "/nanda/weekday_bus_schedule_toward_main_campus",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {"time": "7:20", "description": ""},
                        {"time": "7:33", "description": "此為付費市區公車(83號公車直達兩校區)"},
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[Schedule],
)
async def get_nanda_weekday_bus_schedule_toward_main_campus():
    """
    南大往本部區間車時刻表（平日）。
    """
    return buses.get_nanda_data()["weekday_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/weekend_bus_schedule_toward_main_campus",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {"time": "8:00", "description": ""},
                        {"time": "12:00", "description": ""},
                        {"time": "14:00", "description": ""},
                        {"time": "17:00", "description": ""},
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[Schedule],
)
async def get_nanda_weekend_bus_schedule_toward_main_campus():
    """
    南大往本部區間車時刻表（假日）。
    """
    return buses.get_nanda_data()["weekend_bus_schedule_toward_main_campus"]
