from enum import Enum
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, HttpUrl, Field

from ..models.dining import Dining


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


router = APIRouter(
    prefix="/dining",
    tags=["dining"],
    responses={404: {"description": "Not found"}},
)

dining = Dining()


@router.get(
    "/",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "building": "小吃部",
                            "restaurants": [
                                {
                                    "area": "小吃部",
                                    "image": "https://img.onl/CYp5nN",
                                    "name": "7-ELEVEN",
                                    "note": "",
                                    "phone": "0920-229-711, 03-5166254",
                                    "schedule": {
                                        "saturday": "24小時",
                                        "sunday": "24小時",
                                        "weekday": "24小時",
                                    },
                                },
                                {
                                    "...",
                                },
                            ],
                        },
                    ]
                },
            },
        },
    },
    response_model=list[DiningBuilding],
)
def get_dining_data() -> list[DiningBuilding]:
    """
    取得所有餐廳資料。
    """
    return dining.get_dining_data()


@router.get(
    "/buildings",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": ["小吃部", "水木生活中心", "風雲樓", "綜合教學大樓(南大校區)", "其他餐廳"]
                },
            },
        },
    },
    response_model=list[DiningBuildingName],
)
def get_all_building_names() -> list[DiningBuildingName]:
    """
    取得所有建築名稱。
    """
    return dining.get_all_building_names()


@router.get(
    "/buildings/{building_name}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "building": "小吃部",
                        "restaurants": [
                            {
                                "area": "小吃部",
                                "image": "https://img.onl/CYp5nN",
                                "name": "7-ELEVEN",
                                "note": "",
                                "phone": "0920-229-711, 03-5166254",
                                "schedule": {
                                    "saturday": "24小時",
                                    "sunday": "24小時",
                                    "weekday": "24小時",
                                },
                            },
                            {
                                "...",
                            },
                        ],
                    }
                },
            },
        },
    },
    response_model=DiningBuilding,
)
def get_dining_data(
    building_name: DiningBuildingName = Path(..., example="小吃部", description="建築名稱")
) -> DiningBuilding:
    """
    使用建築名稱取得指定建築的餐廳資料。
    """
    return dining.query_by_building_name(building_name)


@router.get(
    "/restaurants",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": ["7-ELEVEN", "麥當勞", "瑞斯飯糰", "漢城異國美食", "對味", "..."]
                },
            },
        },
    },
    response_model=list[str],
)
def get_all_restaurant_names() -> list[str]:
    """
    取得所有餐廳名稱。
    """
    return dining.get_all_restaurant_names()


@router.get(
    "/restaurants/{restaurant_name}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "area": "小吃部",
                        "image": "https://img.onl/KvsZAz",
                        "name": "麥當勞",
                        "note": "",
                        "phone": "03-5727801",
                        "schedule": {
                            "saturday": "7:00-24:00",
                            "sunday": "7:00-24:00",
                            "weekday": "7:00-24:00",
                        },
                    }
                },
            },
        },
    },
    response_model=list[DiningRestaurant],
)
def get_dining_data(
    restaurant_name: str = Path(..., example="麥當勞", description="餐廳名稱")
):
    """
    使用餐廳名稱取得指定餐廳資料。
    """
    return dining.query_by_restaurant_name(restaurant_name)


@router.get(
    "/scedules/{day_of_week}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "area": "小吃部",
                            "image": "https://img.onl/KvsZAz",
                            "name": "麥當勞",
                            "note": "",
                            "phone": "03-5727801",
                            "schedule": {
                                "saturday": "7:00-24:00",
                                "sunday": "7:00-24:00",
                                "weekday": "7:00-24:00",
                            },
                        },
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[DiningRestaurant],
)
def get_schedule_by_day_of_week(
    day_of_week: DiningSceduleName = Path(..., example="saturday", description="營業日")
) -> list[DiningRestaurant]:
    """
    取得所有該營業日的餐廳資訊。
    """
    try:
        return dining.query_by_schedule(day_of_week)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/searches/restaurants/{restaurant_name}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "area": "小吃部",
                            "image": "https://img.onl/KvsZAz",
                            "name": "麥當勞",
                            "note": "",
                            "phone": "03-5727801",
                            "schedule": {
                                "saturday": "7:00-24:00",
                                "sunday": "7:00-24:00",
                                "weekday": "7:00-24:00",
                            },
                        },
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[DiningRestaurant],
)
def fuzzy_search_restaurant_by_name(
    restaurant_name: str = Path(..., example="麵", description="餐廳名稱")
) -> List[DiningRestaurant]:
    """
    使用餐廳名稱模糊搜尋餐廳資料。
    """
    return dining.fuzzy_search_restaurant_by_name(restaurant_name)
