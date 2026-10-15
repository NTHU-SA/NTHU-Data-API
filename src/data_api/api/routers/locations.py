"""Locations router."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from data_api.api.schemas import locations as schemas
from data_api.api.schemas.responses import SNAPSHOT_RESPONSES
from data_api.runtime import get_runtime

router = APIRouter(responses=SNAPSHOT_RESPONSES)


@router.get("", response_model=list[schemas.LocationDetail], operation_id="getLocations")
async def get_locations(
    response: Response,
    name: Annotated[str | None, Query(description="地點名稱；未提供或為空時回傳所有地點")] = None,
    fuzzy: Annotated[
        bool, Query(description="是否進行模糊搜尋，若不啟用則必須完全符合（不建議）")
    ] = True,
):
    """
    取得校內地點資訊；預設使用名稱模糊搜尋，fuzzy=false 時須完全符合。
    未提供名稱或為空時回傳所有地點，無結果時回傳空陣列。
    資料來源：[國立清華大學校園地圖](https://www.nthu.edu.tw/campusmap)
    """
    if name and fuzzy:
        commit_hash, data = await get_runtime().locations.fuzzy_search_locations(query=name)
    else:
        commit_hash, data = await get_runtime().locations.get_locations(name=name)
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
