"""
Dining router.

Handles HTTP endpoints for dining information.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from data_api.api.schemas import dining as schemas
from data_api.domain.dining import services

router = APIRouter()


@router.get("/", response_model=list[schemas.DiningBuilding], operation_id="getDiningData")
async def get_dining_data(
    response: Response,
    building_name: schemas.DiningBuildingName = Query(None, description="餐廳建築名稱（可選）"),
    restaurant_name: str = Query(None, description="餐廳名稱（可選）"),
    fuzzy: bool = Query(True, description="是否進行模糊搜尋，若不啟用則必須完全符合（不建議）"),
) -> list[schemas.DiningBuilding]:
    """
    取得所有餐廳及廠商資料。
    資料來源：[總務處經營管理組](https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw)
    """
    if fuzzy:
        commit_hash, data = await services.dining_service.fuzzy_search_dining_data(
            building_name=building_name,
            restaurant_name=restaurant_name,
        )
    else:
        commit_hash, data = await services.dining_service.get_dining_data(
            building_name=building_name,
            restaurant_name=restaurant_name,
        )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/open",
    response_model=list[schemas.DiningRestaurant],
    operation_id="getOpenRestaurants",
)
async def get_open_restaurants(
    response: Response,
    schedule: schemas.DiningScheduleName = Query(..., description="營業時間查詢"),
):
    """取得指定營業日的餐廳資料。"""
    commit_hash, data = await services.dining_service.get_open_restaurants(schedule=schedule)
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
