"""REST bus query parameters and shared response models."""

from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field

from data_api.models.buses import (
    BusArriveTime,
    BusCanonicalDetailedSchedule,
    BusCanonicalSchedule,
    BusDay,
    BusDayWithCurrent,
    BusDetailedSchedule,
    BusDirection,
    BusInfo,
    BusRouteType,
    BusSchedule,
    BusStopsInfo,
    BusStopsName,
    BusType,
)

__all__ = [
    "BusArriveTime",
    "BusCanonicalDetailedSchedule",
    "BusCanonicalSchedule",
    "BusDay",
    "BusDayWithCurrent",
    "BusDetailedSchedule",
    "BusDirection",
    "BusInfo",
    "BusQuery",
    "BusRouteType",
    "BusSchedule",
    "BusStopsInfo",
    "BusStopsName",
    "BusType",
]


class BusQuery(BaseModel):
    """Query parameters for bus endpoints."""

    time: Optional[str] = Field(
        Query(None, description="時間。若搜尋 day 選擇 current 時失效。"),
        description="時間",
    )
    limit: Optional[int] = Field(
        Query(
            5,
            ge=1,
            description="最大回傳資料筆數。預設為 5 筆，可以透過查詢參數調整。",
        ),
        description="最大回傳資料筆數",
    )
