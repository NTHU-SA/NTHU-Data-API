from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class DiningBuildingName(str, Enum):
    小吃部 = "小吃部"
    水木生活中心 = "水木生活中心"
    風雲樓 = "風雲樓"
    綜合教學大樓_南大校區 = "綜合教學大樓(南大校區)"
    其他餐廳 = "其他餐廳"


class DiningSceduleName(str, Enum):
    weekday = "weekday"
    saturday = "saturday"
    sunday = "sunday"


class DiningRestaurant(BaseModel):
    area: str = Field(..., description="餐廳所在建築")
    image: Optional[HttpUrl] = Field(..., description="餐廳圖片")
    name: str = Field(..., description="餐廳名稱")
    note: str = Field(..., description="餐廳備註")
    phone: str = Field(..., description="餐廳電話")
    schedule: dict = Field(..., description="餐廳營業時間")


class DiningBuilding(BaseModel):
    building: str = Field(..., description="建築名稱")
    restaurants: list[DiningRestaurant] = Field(..., description="餐廳資料")
