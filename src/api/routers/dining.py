from fastapi import APIRouter, HTTPException
from ..models.dining import Dining

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
)
def get_dining_data():
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
)
def get_all_building_names():
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
)
def get_dining_data(building_name: str):
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
)
def get_all_restaurant_names():
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
)
def get_dining_data(
    restaurant_name: str,
):
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
)
def get_scheduled_on_saturday():
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
)
def get_scheduled_on_sunday():
    try:
        return dining.get_scheduled_on_sunday()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
