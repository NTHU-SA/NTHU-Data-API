from enum import Enum
from typing import Optional
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, HttpUrl, Field

from ..models.dining import Dining


class Schedule(BaseModel):
    saturday: str = Field(..., description="星期六營業時間")
    sunday: str = Field(..., description="星期日營業時間")
    weekday: str = Field(..., description="平日營業時間")


class BuildingName(str, Enum):
    小吃部 = "小吃部"
    水木生活中心 = "水木生活中心"
    風雲樓 = "風雲樓"
    綜合教學大樓_南大校區 = "綜合教學大樓(南大校區)"
    其他餐廳 = "其他餐廳"


class Restaurant(BaseModel):
    area: str = Field(..., description="餐廳所在建築")
    image: Optional[HttpUrl] = Field(..., description="餐廳圖片")
    name: str = Field(..., description="餐廳名稱")
    note: str = Field(..., description="餐廳備註")
    phone: str = Field(..., description="餐廳電話")
    schedule: dict = Field(..., description="餐廳營業時間")


class Building(BaseModel):
    building: str = Field(..., description="建築名稱")
    restaurants: list[Restaurant] = Field(..., description="餐廳資料")


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
    response_model=list[Building],
)
def get_dining_data():
    """
    取得所有餐廳資料。
    """
    try:
        return dining.get_dining_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    response_model=list[BuildingName],
)
def get_all_building_names():
    """
    取得所有建築名稱。
    """
    try:
        return dining.get_all_building_names()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    response_model=Building,
)
def get_dining_data(building_name: BuildingName = Path(..., description="建築名稱")):
    """
    使用建築名稱取得指定建築的餐廳資料。
    """
    try:
        return dining.query_by_building_name(building_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
def get_all_restaurant_names():
    """
    取得所有餐廳名稱。
    """
    try:
        return dining.get_all_restaurant_names()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    response_model=list[Restaurant],
)
def get_dining_data(restaurant_name: str = Path(..., description="餐廳名稱")):
    """
    使用餐廳名稱取得指定餐廳資料。
    """
    try:
        return dining.query_by_restaurant_name(restaurant_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sceduled/saturday",
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
    response_model=list[Restaurant],
)
def get_scheduled_on_saturday():
    """
    取得所有星期六有營業的餐廳資訊。
    """
    try:
        return dining.get_scheduled_on_saturday()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/sceduled/sunday",
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
    response_model=list[Restaurant],
)
def get_scheduled_on_sunday():
    """
    取得所有星期日有營業的餐廳資訊。
    """
    try:
        return dining.get_scheduled_on_sunday()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
