import re
from enum import Enum
from typing import Optional

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field, field_validator


class StopsName(str, Enum):
    M1 = "北校門口"
    M2 = "綜二館"
    M3 = "楓林小徑"
    M4 = "人社院/生科館"
    M5 = "台積館"
    M6 = "奕園停車場"
    M7 = "南門停車場"
    S1 = "南大校區校門口右側(食品路校牆邊)"


class BusType(str, Enum):
    all = "all"
    main = "main"
    nanda = "nanda"


class BusDirection(str, Enum):
    up = "up"
    down = "down"


class BusDay(str, Enum):
    all = "all"
    weekday = "weekday"
    weekend = "weekend"


class BusQuery(BaseModel):
    time: Optional[str] = Field(
        Query("0:00", example="8:10", description="時間"), description="時間"
    )
    limits: Optional[int] = Field(
        Query(None, ge=1, description="最大回傳資料筆數"), description="最大回傳資料筆數"
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
    direction: str = Field(..., description="方向")
    duration: str = Field(..., description="時刻表有效期間")
    route: str = Field(..., description="路線")
    routeEN: str = Field(..., description="英文路線")


class BusNandaSchedule(BaseModel):
    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")
    route: str = Field("南大區間車", description="路線")


class BusMainSchedule(BaseModel):
    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")
    route: str = Field("校園公車", description="路線")
    depStop: str = Field(..., description="發車地點")
    line: str = Field(..., description="路線")


class BusStopsQueryResult(BaseModel):
    bus_info: BusNandaSchedule | BusMainSchedule = Field(..., description="公車資訊")
    arrive_time: str = Field(..., description="預計到達時間")


class BusArriveTime(BaseModel):
    # {"stop_name": stop.name, "time": arrive_time}
    stop_name: StopsName = Field(..., description="公車站牌名稱")
    time: str = Field(..., description="預計到達時間")


class BusNandaDetailedSchedule(BaseModel):
    dep_info: BusNandaSchedule = Field(..., description="發車資訊")
    stops_time: list[BusArriveTime] = Field(..., description="各站發車時間")


class BusMainDetailedSchedule(BaseModel):
    dep_info: BusMainSchedule = Field(..., description="發車資訊")
    stops_time: list[BusArriveTime] = Field(..., description="各站發車時間")


class BusMainData(BaseModel):
    toward_TSMC_building_info: BusInfo = Field(..., description="校門口往台積館公車資訊")
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
    toward_south_campus_info: BusInfo = Field(..., description="本部往南大區間車資訊")
    weekday_bus_schedule_toward_south_campus: list[BusNandaSchedule] = Field(
        ..., description="本部往南大區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_south_campus: list[BusNandaSchedule] = Field(
        ..., description="本部往南大區間車時刻表（假日）"
    )
    toward_main_campus_info: BusInfo = Field(..., description="南大往本部區間車資訊")
    weekday_bus_schedule_toward_main_campus: list[BusNandaSchedule] = Field(
        ..., description="南大往本部區間車時刻表（平日）"
    )
    weekend_bus_schedule_toward_main_campus: list[BusNandaSchedule] = Field(
        ..., description="南大往本部區間車時刻表（假日）"
    )
