"""Locations router."""

from fastapi import APIRouter, HTTPException, Query, Response

from data_api.api.schemas import locations as schemas
from data_api.domain.locations import services

router = APIRouter()


@router.get("/", response_model=list[schemas.LocationDetail])
async def get_all_locations(response: Response):
    """
    取得校內所有地點資訊。
    資料來源：[國立清華大學校園地圖](https://www.nthu.edu.tw/campusmap)
    """
    commit_hash, data = await services.locations_service.get_all_locations()
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get("/search", response_model=list[schemas.LocationDetail])
async def fuzzy_search_locations(
    response: Response,
    query: str = Query(..., example="校門", description="要查詢的地點"),
):
    """使用名稱模糊搜尋地點資訊。"""
    commit_hash, data = await services.locations_service.fuzzy_search_locations(
        query=query
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if not data:
        raise HTTPException(status_code=404, detail="Not found")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
