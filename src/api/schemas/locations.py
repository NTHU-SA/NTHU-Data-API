from pydantic import BaseModel, Field


class LocationDetail(BaseModel):
    name: str = Field(..., description="地點名稱")
    latitude: str = Field(..., description="地點緯度")
    longitude: str = Field(..., description="地點經度")
