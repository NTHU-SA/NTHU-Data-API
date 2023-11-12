from pydantic import BaseModel, Field


class BusInfo(BaseModel):
    direction: str = Field(..., description="方向")
    duration: str = Field(..., description="時刻表有效期間")
    route: str = Field(..., description="路線")
    routeEN: str = Field(..., description="英文路線")


class BusNandaSchedule(BaseModel):
    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")


class BusMainSchedule(BaseModel):
    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")
    depStop: str = Field(..., description="發車地點")
    line: str = Field(..., description="路線")


class BusMainData(BaseModel):
    toward_TSMC_building_info: BusInfo = Field(..., description="校門口往台積館公車資訊")
    weekday_bus_schedule_toward_TSMC_building: list[BusNandaSchedule] = Field(
        ..., description="校門口往台積館公車時刻表（平日）"
    )
    weekend_bus_schedule_toward_TSMC_building: list[BusNandaSchedule] = Field(
        ..., description="校門口往台積館公車時刻表（假日）"
    )
    toward_main_gate_info: BusInfo = Field(..., description="台積館往校門口公車資訊")
    weekday_bus_schedule_toward_main_gate: list[BusNandaSchedule] = Field(
        ..., description="台積館往校門口公車時刻表（平日）"
    )
    weekend_bus_schedule_toward_main_gate: list[BusNandaSchedule] = Field(
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
