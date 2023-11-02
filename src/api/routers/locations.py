from fastapi import APIRouter, HTTPException
from ..models.locations import Location

router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    responses={404: {"description": "Not found"}},
)

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
)
def get_all_location():
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
)
def search_location(query: str, max_result: int = 10):
    result = location.fuzzy_search(query)
    result = result[:max_result]
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get(
    "/{query}",
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
)
def get_location(query: str):
    result = location.get_by_id(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")


@router.get(
    "/searches/{query}",
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
)
def search_location(query: str):
    result = location.fuzzy_search(query)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result
