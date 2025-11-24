"""Locations router."""

from fastapi import APIRouter, HTTPException, Query, Response

from data_api.api.schemas import locations as schemas
from data_api.domain.locations import services

router = APIRouter()


@router.get("/", response_model=list[schemas.LocationDetail])
async def get_all_locations(response: Response):
    """
    Get all campus location information.
    Data source: NTHU Campus Map
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
    """Fuzzy search locations by name."""
    commit_hash, data = await services.locations_service.fuzzy_search_locations(
        query=query
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if not data:
        raise HTTPException(status_code=404, detail="Not found")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
