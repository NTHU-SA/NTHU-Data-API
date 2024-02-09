from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from src.api import schemas
from src.api.models.locations import Location

router = APIRouter()
location = Location()
NOT_FOUND_EXCEPTION = HTTPException(status_code=404, detail="Not found")


@router.get("/", response_model=list[schemas.locations.LocationData])
def get_all_location():
    """
    取得所有地點資訊。
    """
    result = location.get_all()
    return result


@router.get("/{id}", response_model=schemas.locations.LocationData)
def get_location_by_id(
    id: UUID = Path(
        ...,
        example="b876aa09-40a8-427b-8bc7-1933978690e2",
        description="要查詢的地點 id",
    )
):
    """
    使用地點 id 取得指定地點資訊。
    """
    result = location.get_by_id(id)
    if result:
        return result
    raise NOT_FOUND_EXCEPTION


@router.get("/searches/{name}", response_model=list[schemas.locations.LocationData])
def search_location_by_get_method(
    name: str = Path(..., example="校門", description="要查詢的地點")
):
    """
    使用名稱模糊搜尋地點資訊。
    """
    result = location.fuzzy_search(name)
    if result:
        return result
    raise NOT_FOUND_EXCEPTION


@router.post("/searches", response_model=list[schemas.locations.LocationData])
def search_location_by_post_method(search_data: schemas.locations.LocationSearchData):
    """
    使用名稱模糊搜尋地點資訊。
    """
    result = location.fuzzy_search(search_data.name)
    result = result[: search_data.max_result]
    if result:
        return result
    raise NOT_FOUND_EXCEPTION
