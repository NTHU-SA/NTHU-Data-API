from uuid import UUID

from pydantic import BaseModel, Field


class LocationDetail(BaseModel):
    name: str = Field(..., description="地點名稱")
    name_en: str = Field(..., description="地點英文名稱")
    latitude: str = Field(..., description="地點緯度")
    longitude: str = Field(..., description="地點經度")


class LocationData(BaseModel):
    id: UUID = Field(..., description="地點 id")
    data: LocationDetail = Field(..., description="地點資料")
    create_time: str = Field(..., description="建立時間")
    update_time: str = Field(..., description="更新時間")


class LocationSearchData(BaseModel):
    name: str = Field(..., description="要查詢的地點")
    max_result: int = Field(10, description="最多回傳幾筆資料")
