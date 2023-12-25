from fastapi import APIRouter, HTTPException, Path

from src.api import schemas
from src.api.models.dining import Dining

router = APIRouter()
dining = Dining()


@router.get("/", response_model=list[schemas.dining.DiningBuilding])
def get_all_dining_data() -> list[schemas.dining.DiningBuilding]:
    """
    取得所有餐廳資料。
    """
    return dining.get_dining_data()


@router.get("/buildings", response_model=list[schemas.dining.DiningBuildingName])
def get_all_building_names() -> list[schemas.dining.DiningBuildingName]:
    """
    取得所有建築名稱。
    """
    return dining.get_all_building_names()


@router.get("/buildings/{building_name}", response_model=schemas.dining.DiningBuilding)
def get_dining_data_in_buildings(
    building_name: schemas.dining.DiningBuildingName = Path(
        ..., example="小吃部", description="建築名稱"
    )
) -> schemas.dining.DiningBuilding:
    """
    使用建築名稱取得指定建築的餐廳資料。
    """
    return dining.query_by_building_name(building_name)


@router.get("/restaurants", response_model=list[str])
def get_all_restaurant_names() -> list[str]:
    """
    取得所有餐廳名稱。
    """
    return dining.get_all_restaurant_names()


@router.get(
    "/restaurants/{restaurant_name}",
    response_model=list[schemas.dining.DiningRestaurant],
)
def get_dining_data_by_name(
    restaurant_name: str = Path(..., example="麥當勞", description="餐廳名稱")
):
    """
    使用餐廳名稱取得指定餐廳資料。
    """
    return dining.query_by_restaurant_name(restaurant_name)


@router.get(
    "/schedules/{day_of_week}", response_model=list[schemas.dining.DiningRestaurant]
)
def get_schedule_by_day_of_week(
    day_of_week: schemas.dining.DiningSceduleName = Path(
        ..., example="saturday", description="營業日"
    )
) -> list[schemas.dining.DiningRestaurant]:
    """
    取得所有該營業日的餐廳資訊。
    """
    try:
        return dining.query_by_schedule(day_of_week)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/searches/restaurants/{restaurant_name}",
    response_model=list[schemas.dining.DiningRestaurant],
)
def fuzzy_search_restaurant_by_name(
    restaurant_name: str = Path(..., example="麵", description="餐廳名稱")
) -> list[schemas.dining.DiningRestaurant]:
    """
    使用餐廳名稱模糊搜尋餐廳資料。
    """
    return dining.fuzzy_search_restaurant_by_name(restaurant_name)
