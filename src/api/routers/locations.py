from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from uuid import UUID

from ..models.locations import Location


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


router = APIRouter()
location = Location()


@router.get("/", response_model=list[LocationData])
def get_all_location():
    """
    取得所有地點資訊。
    """
    result = location.get_all()
    return result


@router.get("/{id}", response_model=LocationData)
def get_location_by_id(
    id: UUID = Path(
        ..., example="b876aa09-40a8-427b-8bc7-1933978690e2", description="要查詢的地點 id"
    )
):
    """
    使用地點 id 取得指定地點資訊。
    """
    result = location.get_by_id(id)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/searches/{name}", response_model=list[LocationData])
def search_location_by_get_method(
    name: str = Path(..., example="校門", description="要查詢的地點")
):
    """
    使用名稱模糊搜尋地點資訊。
    """
    result = location.fuzzy_search(name)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    return result


@router.post("/searches", response_model=list[LocationData])
def search_location_by_post_method(search_data: LocationSearchData):
    """
    使用名稱模糊搜尋地點資訊。
    """
    result = location.fuzzy_search(search_data.name)
    result = result[: search_data.max_result]
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    return result
