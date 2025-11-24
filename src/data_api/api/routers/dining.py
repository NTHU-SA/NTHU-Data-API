"""
Dining router.

Handles HTTP endpoints for dining information.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from data_api.api.schemas import dining as schemas
from data_api.domain.dining import services

router = APIRouter()


@router.get("/", response_model=list[schemas.DiningBuilding])
async def get_dining_data(
    response: Response,
    building_name: schemas.DiningBuildingName = Query(
        None, example="小吃部", description="餐廳建築名稱（可選）"
    ),
) -> list[schemas.DiningBuilding]:
    """
    Get all restaurant and service vendor data.
    Data source: General Affairs Office
    """
    commit_hash, data = await services.dining_service.get_dining_data(
        building_name=building_name
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get("/open", response_model=list[schemas.DiningRestaurant])
async def get_open_restaurants(
    response: Response,
    schedule: schemas.DiningScheduleName = Query(
        ..., example="today", description="營業時間查詢"
    ),
):
    """Get currently open restaurants."""
    commit_hash, data = await services.dining_service.get_open_restaurants(
        schedule=schedule
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get("/search", response_model=list[schemas.DiningRestaurant])
async def fuzzy_search_restaurants(
    response: Response,
    query: str = Query(..., example="麥當勞", description="要查詢的餐廳名稱"),
):
    """Fuzzy search restaurants by name."""
    commit_hash, data = await services.dining_service.fuzzy_search_restaurants(
        query=query
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    
    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
