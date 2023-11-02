from fastapi import APIRouter, HTTPException
from ..models.buses import Buses

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
            "description": "南大校區區間車資訊",
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
)
async def get_nanda():
    return buses.get_nanda_data()


@router.get(
    "/nanda/toward_south_campus_info",
    responses={
        200: {
            "description": "本部往南大區間車資訊",
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
)
async def get_nanda_toward_south_campus_info():
    return buses.get_nanda_data()["toward_south_campus_info"]


@router.get(
    "/nanda/weekday_bus_schedule_toward_south_campus",
    responses={
        200: {
            "description": "本部往南大區間車時刻表（平日）",
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
)
async def get_nanda_weekday_bus_schedule_toward_south_campus():
    return buses.get_nanda_data()["weekday_bus_schedule_toward_south_campus"]


@router.get(
    "/nanda/weekend_bus_schedule_toward_south_campus",
    responses={
        200: {
            "description": "本部往南大區間車時刻表（假日）",
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
)
async def get_nanda_weekend_bus_schedule_toward_south_campus():
    return buses.get_nanda_data()["weekend_bus_schedule_toward_south_campus"]


@router.get(
    "/nanda/toward_main_campus_info",
    responses={
        200: {
            "description": "南大往本部區間車資訊",
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
)
async def get_nanda_toward_main_campus_info():
    return buses.get_nanda_data()["toward_main_campus_info"]


@router.get(
    "/nanda/weekday_bus_schedule_toward_main_campus",
    responses={
        200: {
            "description": "南大往本部區間車時刻表（平日）",
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
)
async def get_nanda_weekday_bus_schedule_toward_main_campus():
    return buses.get_nanda_data()["weekday_bus_schedule_toward_main_campus"]


@router.get(
    "/nanda/weekend_bus_schedule_toward_main_campus",
    responses={
        200: {
            "description": "南大往本部區間車時刻表（假日）",
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
)
async def get_nanda_weekend_bus_schedule_toward_main_campus():
    return buses.get_nanda_data()["weekend_bus_schedule_toward_main_campus"]
