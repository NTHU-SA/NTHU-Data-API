"""
Bus API schemas.

Pydantic models for request/response validation.
Enums are imported from domain layer to avoid duplication.
"""

import re
from typing import Optional

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field, field_validator

# Import enums from domain
from data_api.domain.buses.enums import (
    BusDay,
    BusDayWithCurrent,
    BusDirection,
    BusRouteType,
    BusStopsName,
    BusType,
)

__all__ = [
    "BusStopsName",
    "BusRouteType",
    "BusType",
    "BusDirection",
    "BusDay",
    "BusDayWithCurrent",
    "BusQuery",
    "BusInfo",
    "BusStopsInfo",
    "BusNandaSchedule",
    "BusMainSchedule",
    "BusStopsQueryResult",
    "BusArriveTime",
    "BusNandaDetailedSchedule",
    "BusMainDetailedSchedule",
    "BusMainData",
    "BusNandaData",
]


class BusQuery(BaseModel):
    """Query parameters for bus endpoints."""

    time: Optional[str] = Field(
        Query(None, description="時間。若搜尋 day 選擇 current 時失效。"),
        description="時間",
    )
    limits: Optional[int] = Field(
        Query(
            None,
            ge=1,
            description="最大回傳資料筆數。若搜尋 day 選擇 current 且大於 5 時失效。",
        ),
        description="最大回傳資料筆數",
    )

    @field_validator("time")
    def validate_time(cls, v):
        splited = v.split(":")
        if len(splited) != 2:
            raise HTTPException(
                status_code=422, detail="Time must be in format of HH:MM or H:MM."
            )
        elif re.match(r"^\d{1,2}$", splited[0]) is None:
            raise HTTPException(
                status_code=422, detail="Hour must be in format of HH or H."
            )
        elif re.match(r"^\d{2}$", splited[1]) is None:
            raise HTTPException(
                status_code=422, detail="Minute must be in format of MM."
            )
        elif int(splited[0]) < 0 or int(splited[0]) > 23:
            raise HTTPException(
                status_code=422, detail="Hour must be positive and less than 24."
            )
        elif int(splited[1]) < 0 or int(splited[1]) > 59:
            raise HTTPException(
                status_code=422, detail="Minute must be positive and less than 60."
            )
        return v


class BusInfo(BaseModel):
    """Bus route information."""

    direction: str = Field(..., description="方向")
    duration: str = Field(..., description="時刻表有效期間")
    route: str = Field(..., description="路線")
    routeEN: str = Field(..., description="英文路線")


class BusStopsInfo(BaseModel):
    """Bus stop information."""

    name: str = Field(..., description="站牌中文名稱")
    name_en: str = Field(..., description="站牌英文名稱")
    latitude: str = Field(..., description="站牌所在地緯度")
    longitude: str = Field(..., description="站牌所在地經度")


class BusNandaSchedule(BaseModel):
    """Nanda campus bus schedule entry."""

    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")
    dep_stop: str = Field(..., description="發車地點")
    bus_type: BusType = Field(..., description="營運車輛類型")


class BusMainSchedule(BaseModel):
    """Main campus bus schedule entry."""

    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")
    dep_stop: str = Field(..., description="發車地點")
    line: str = Field(..., description="路線")
    bus_type: BusType = Field(..., description="營運車輛類型")


class BusStopsQueryResult(BaseModel):
    """Result of querying bus stops."""

    arrive_time: str = Field(..., description="預計到達時間")
    dep_time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")
    bus_type: BusType = Field(..., description="營運車輛類型")


class BusArriveTime(BaseModel):
    """Bus arrival time at a stop."""

    stop: str = Field(..., description="公車站牌名稱")
    arrive_time: str = Field(..., description="預計到達時間")


class BusNandaDetailedSchedule(BaseModel):
    """Detailed Nanda campus bus schedule."""

    dep_info: BusNandaSchedule = Field(..., description="發車資訊")
    stops_time: list[BusArriveTime] = Field(..., description="各站發車時間")


class BusMainDetailedSchedule(BaseModel):
    """Detailed main campus bus schedule."""

    dep_info: BusMainSchedule = Field(..., description="發車資訊")
    stops_time: list[BusArriveTime] = Field(..., description="各站發車時間")


class BusMainData(BaseModel):
    """Main campus bus data."""

    toward_TSMC_building_info: BusInfo = Field(
        ..., description="校門口往台積館公車資訊"
    )
    weekday_bus_schedule_toward_TSMC_building: list[BusMainSchedule] = Field(
        ..., description="校門口往台積館公車時刻表（平日）"
    )
    weekend_bus_schedule_toward_TSMC_building: list[BusMainSchedule] = Field(
        ..., description="校門口往台積館公車時刻表（假日）"
    )
    toward_main_gate_info: BusInfo = Field(..., description="台積館往校門口公車資訊")
    weekday_bus_schedule_toward_main_gate: list[BusMainSchedule] = Field(
        ..., description="台積館往校門口公車時刻表（平日）"
    )
    weekend_bus_schedule_toward_main_gate: list[BusMainSchedule] = Field(
        ..., description="台積館往校門口公車時刻表（假日）"
    )


class BusNandaData(BaseModel):
    """Nanda campus bus data."""

    toward_nanda_info: BusInfo = Field(..., description="本部往南大區間車資訊")
    weekday_bus_schedule_toward_nanda: list[BusNandaSchedule] = Field(
        ..., description="本部往南大區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_nanda: list[BusNandaSchedule] = Field(
        ..., description="本部往南大區間車時刻表（假日）"
    )
    toward_main_campus_info: BusInfo = Field(..., description="南大往本部區間車資訊")
    weekday_bus_schedule_toward_main_campus: list[BusNandaSchedule] = Field(
        ..., description="南大往本部區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_main_campus: list[BusNandaSchedule] = Field(
        ..., description="南大往本部區間車時刻表（假日）"
    )
