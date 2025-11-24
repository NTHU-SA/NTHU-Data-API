"""Locations API schemas."""

from pydantic import BaseModel, Field


class LocationDetail(BaseModel):
    """Location detail information."""

    name: str = Field(..., description="地點名稱")
    latitude: str = Field(..., description="緯度")
    longitude: str = Field(..., description="經度")
