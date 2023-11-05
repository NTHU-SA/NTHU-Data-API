from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from uuid import UUID

from ..models.locations import Location


class Data(BaseModel):
    name: str = Field(..., description="地點名稱")
    name_en: str = Field(..., description="地點英文名稱")
    latitude: str = Field(..., description="地點緯度")
    longitude: str = Field(..., description="地點經度")


class LocationData(BaseModel):
    id: UUID = Field(..., description="地點 id")
    data: Data = Field(..., description="地點資料")
    create_time: str = Field(..., description="建立時間")
    update_time: str = Field(..., description="更新時間")


class SearchData(BaseModel):
    name: str = Field(..., description="要查詢的地點")
    max_result: int = Field(10, description="最多回傳幾筆資料")


router = APIRouter()
location = Location()


@router.get(
    "/",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "b876aa09-40a8-427b-8bc7-1933978690e2",
                            "data": {
                                "name": "光復路校門",
                                "name_en": "North gate",
                                "latitude": "24.796538",
                                "longitude": "120.997015",
                            },
                            "create_time": "20231014T225400+0800",
                            "update_time": "20231014T225400+0800",
                        },
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[LocationData],
)
def get_all_location():
    """
    取得所有地點資訊。
    """
    try:
        result = location.get_all()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post(
    "/searches",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "82f872a8-a0f3-41df-bf6f-1df741e1cbcd",
                            "data": {
                                "name": "台積館",
                                "name_en": "TSMC Building",
                                "latitude": "24.78699",
                                "longitude": "120.98795",
                            },
                            "create_time": "20231014T225400+0800",
                            "update_time": "20231014T225400+0800",
                        },
                        {
                            "id": "7255f0d9-8eee-47b2-9165-20db7950fc0d",
                            "data": {
                                "name": "台達館",
                                "name_en": "DeltaHall",
                                "latitude": "24.79591",
                                "longitude": "120.99211",
                            },
                            "create_time": "20231014T225400+0800",
                            "update_time": "20231014T225400+0800",
                        },
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[LocationData],
)
def search_location(search_data: SearchData):
    """
    使用名稱模糊搜尋地點資訊。
    """
    result = location.fuzzy_search(search_data.name)
    result = result[: search_data.max_result]
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get(
    "/{id}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "id": "27833bfe-e387-4a8a-a182-9b617780e927",
                        "data": {
                            "name": "動機化學實驗館",
                            "name_en": "Chemistry and Power Mechanical Engineering Building",
                            "latitude": "24.796533",
                            "longitude": "120.995204",
                        },
                        "create_time": "20231014T225400+0800",
                        "update_time": "20231014T225400+0800",
                    }
                },
            },
        },
    },
    response_model=LocationData,
)
def get_location(id: UUID = Path(..., description="要查詢的地點 id")):
    """
    使用地點 id 取得指定地點資訊。
    """
    result = location.get_by_id(id)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")


@router.get(
    "/searches/{name}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "82f872a8-a0f3-41df-bf6f-1df741e1cbcd",
                            "data": {
                                "name": "台積館",
                                "name_en": "TSMC Building",
                                "latitude": "24.78699",
                                "longitude": "120.98795",
                            },
                            "create_time": "20231014T225400+0800",
                            "update_time": "20231014T225400+0800",
                        },
                        {
                            "id": "7255f0d9-8eee-47b2-9165-20db7950fc0d",
                            "data": {
                                "name": "台達館",
                                "name_en": "DeltaHall",
                                "latitude": "24.79591",
                                "longitude": "120.99211",
                            },
                            "create_time": "20231014T225400+0800",
                            "update_time": "20231014T225400+0800",
                        },
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[LocationData],
)
def search_location(name: str = Path(..., description="要查詢的地點")):
    """
    使用名稱模糊搜尋地點資訊。
    """
    result = location.fuzzy_search(name)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result
