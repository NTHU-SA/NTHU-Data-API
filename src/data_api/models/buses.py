"""
Shared bus response models.

Pydantic models for request/response validation.
Enums are imported from domain layer to avoid duplication.
"""

from pydantic import BaseModel, Field, field_validator

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
    "BusInfo",
    "BusStopsInfo",
    "BusSchedule",
    "BusArriveTime",
    "BusDetailedSchedule",
    "BusCanonicalSchedule",
    "BusCanonicalDetailedSchedule",
]


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


class BusSchedule(BaseModel):
    """Unified bus schedule entry for both Main and Nanda campus."""

    time: str = Field(..., description="發車時間")
    description: str = Field(..., description="備註")
    dep_stop: str = Field(..., description="發車地點")
    line: str = Field("", description="路線 (主校區: red/green, 南大: route_1/route_2)")
    bus_type: BusType = Field(..., description="營運車輛類型")


class BusArriveTime(BaseModel):
    """Bus arrival time at a stop."""

    stop: str = Field(..., description="公車站牌名稱")
    arrive_time: str = Field(..., description="預計到達時間")


class BusDetailedSchedule(BaseModel):
    """Unified detailed bus schedule for both Main and Nanda campus."""

    dep_info: BusSchedule = Field(..., description="發車資訊")
    stops_time: list[BusArriveTime] = Field(..., description="各站發車時間")


class BusCanonicalSchedule(BusSchedule):
    """Schedule with campus-qualified line identifiers for the current API."""

    line: str = Field("", description="路線 (main_red/main_green/nanda_route_1/nanda_route_2)")

    @field_validator("line")
    @classmethod
    def qualify_line(cls, line: str) -> str:
        return {
            "red": "main_red",
            "green": "main_green",
            "route_1": "nanda_route_1",
            "route_2": "nanda_route_2",
        }.get(line, line)


class BusCanonicalDetailedSchedule(BusDetailedSchedule):
    """Detailed schedule with campus-qualified departure line identifiers."""

    dep_info: BusCanonicalSchedule = Field(..., description="發車資訊")
