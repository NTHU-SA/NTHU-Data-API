"""Departments router."""

from typing import Union
from fastapi import APIRouter, HTTPException, Query, Response
from data_api.api.schemas import departments as schemas
from data_api.domain.departments import services

router = APIRouter()


@router.get("/", response_model=list[schemas.Department])
async def get_all_departments(response: Response):
    """Get all departments and personnel."""
    commit_hash, data = await services.departments_service.get_all_departments()
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/search",
    response_model=dict[
        str, Union[list[schemas.Department], list[schemas.DepartmentPerson]]
    ],
)
async def fuzzy_search_departments_and_people(
    response: Response, query: str = Query(..., example="校長")
):
    """Fuzzy search departments and people."""
    commit_hash, data = (
        await services.departments_service.fuzzy_search_departments_and_people(
            query=query
        )
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
