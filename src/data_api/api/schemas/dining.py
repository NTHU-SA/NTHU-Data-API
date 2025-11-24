"""
Dining API schemas.

Pydantic models for dining request/response validation.
"""

from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

from data_api.domain.dining.enums import DiningBuildingName, DiningScheduleName
from data_api.utils.schema import url_corrector

__all__ = ["DiningBuildingName", "DiningScheduleName", "DiningRestaurant", "DiningBuilding"]


class DiningRestaurant(BaseModel):
    """Restaurant information."""

    area: str = Field(..., description="餐廳所在建築")
    image: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = Field(
        ..., description="餐廳圖片"
    )
    name: str = Field(..., description="餐廳名稱")
    note: str = Field(..., description="餐廳備註")
    phone: str = Field(..., description="餐廳電話")
    schedule: dict = Field(..., description="餐廳營業時間")


class DiningBuilding(BaseModel):
    """Building with restaurants."""

    building: str = Field(..., description="建築名稱")
    restaurants: list[DiningRestaurant] = Field(..., description="餐廳資料")
