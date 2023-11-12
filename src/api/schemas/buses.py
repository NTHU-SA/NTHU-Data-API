from pydantic import BaseModel, Field


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
