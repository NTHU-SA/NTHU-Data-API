from fastapi import APIRouter, HTTPException
from ..models.buses import Buses

router = APIRouter(
    prefix="/buses",
    tags=["buses"],
    responses={404: {"description": "Not found"}},
)

buses = Buses()


@router.get("/nanda")
async def get_nanda():
    return buses.get_nanda_data()


@router.get("/nanda/toward_south_campus_info")
async def get_nanda_toward_south_campus_info():
    return buses.get_nanda_data()["toward_south_campus_info"]


@router.get("/nanda/weekday_bus_schedule_toward_south_campus")
async def get_nanda_weekday_bus_schedule_toward_south_campus():
    return buses.get_nanda_data()["weekday_bus_schedule_toward_south_campus"]


@router.get("/nanda/weekend_bus_schedule_toward_south_campus")
async def get_nanda_weekend_bus_schedule_toward_south_campus():
    return buses.get_nanda_data()["weekend_bus_schedule_toward_south_campus"]


@router.get("/nanda/toward_main_campus_info")
async def get_nanda_toward_main_campus_info():
    return buses.get_nanda_data()["toward_main_campus_info"]


@router.get("/nanda/weekday_bus_schedule_toward_main_campus")
async def get_nanda_weekday_bus_schedule_toward_main_campus():
    return buses.get_nanda_data()["weekday_bus_schedule_toward_main_campus"]


@router.get("/nanda/weekend_bus_schedule_toward_main_campus")
async def get_nanda_weekend_bus_schedule_toward_main_campus():
    return buses.get_nanda_data()["weekend_bus_schedule_toward_main_campus"]
