from typing import List

from fastapi import APIRouter, HTTPException, Path, Query

from src.api import schemas
from src.api.models.dining import Dining

router = APIRouter()
dining = Dining()


@router.get("/", response_model=List[schemas.dining.DiningBuilding])
def get_all_dining_data() -> List[schemas.dining.DiningBuilding]:
    """
    取得所有餐廳資料。
    """
    return dining.dining_data


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


@router.get(
    "/schedules/{day_of_week}", response_model=List[schemas.dining.DiningRestaurant]
)
def get_schedule_by_day_of_week(
    day_of_week: schemas.dining.DiningSceduleName = Path(
        ..., example="saturday", description="營業日"
    )
) -> List[schemas.dining.DiningRestaurant]:
    """
    取得所有該營業日的餐廳資訊。
    """
    try:
        return dining.get_open_restaurants_by_day_of_week(day_of_week)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/search",
    response_model=List[schemas.dining.DiningRestaurant],
)
def fuzzy_search_restaurant_by_name(
    restaurant_name: str = Query(..., example="麵", description="餐廳模糊搜尋關鍵字")
) -> List[schemas.dining.DiningRestaurant]:
    """
    使用餐廳名稱模糊搜尋餐廳資料。
    """
    return dining.fuzzy_search_restaurant_by_name(restaurant_name)
