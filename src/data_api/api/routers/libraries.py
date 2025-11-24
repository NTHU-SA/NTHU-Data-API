"""Libraries router."""
from fastapi import APIRouter, HTTPException, Query, Response
from data_api.api.schemas import libraries as schemas
from data_api.domain.libraries import services

router = APIRouter()

@router.get("/", response_model=list[schemas.LibraryInfo])
async def get_all_libraries(response: Response):
    """Get all libraries information."""
    commit_hash, data = await services.libraries_service.get_all_libraries()
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data

@router.get("/search", response_model=list[schemas.LibraryInfo])
async def fuzzy_search_libraries(response: Response, query: str = Query(..., example="總圖")):
    """Fuzzy search libraries by name."""
    commit_hash, data = await services.libraries_service.fuzzy_search_libraries(query=query)
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
