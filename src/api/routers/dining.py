from fastapi import APIRouter, HTTPException
from ..models.dining import Dining

router = APIRouter(
    prefix="/dining",
    tags=["dining"],
    responses={404: {"description": "Not found"}},
)

dining = Dining()


@router.get("/")
def get_dining_data():
    try:
        return dining.get_dining_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buildings")
def get_all_building_names():
    try:
        return dining.get_all_building_names()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buildings/{building_name}")
def get_dining_data(building_name: str):
    try:
        return dining.query_by_building_name(building_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/restaurants")
def get_all_restaurant_names():
    try:
        return dining.get_all_restaurant_names()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/restaurants/{restaurant_name}")
def get_dining_data(restaurant_name: str):
    try:
        return dining.query_by_restaurant_name(restaurant_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sceduled/saturday")
def get_scheduled_on_saturday():
    try:
        return dining.get_scheduled_on_saturday()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sceduled/sunday")
def get_scheduled_on_sunday():
    try:
        return dining.get_scheduled_on_sunday()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
