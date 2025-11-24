"""
Dining router.

Handles HTTP endpoints for dining information.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from data_api.api.schemas import dining as schemas
from data_api.domain.dining import services

router = APIRouter()


@router.get(
    "/", response_model=list[schemas.DiningBuilding], operation_id="getDiningData"
)
async def get_dining_data(
    response: Response,
    building_name: schemas.DiningBuildingName = Query(
        None, description="餐廳建築名稱（可選）"
    ),
) -> list[schemas.DiningBuilding]:
    """
    取得所有餐廳及廠商資料。
    資料來源：[總務處經營管理組](https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw)
    """
    commit_hash, data = await services.dining_service.get_dining_data(
        building_name=building_name
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
    commit_hash, data = await services.dining_service.get_open_restaurants(
        schedule=schedule
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/search",
    response_model=list[schemas.DiningRestaurant],
    operation_id="fuzzySearchRestaurants",
)
async def fuzzy_search_restaurants(
    response: Response,
    query: str = Query(..., description="要查詢的餐廳名稱"),
):
    """使用餐廳名稱模糊搜尋餐廳資料。"""
    commit_hash, data = await services.dining_service.fuzzy_search_restaurants(
        query=query
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
