"""Directory router."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from data_api.api.schemas.departments import Department
from data_api.api.schemas.responses import SNAPSHOT_RESPONSES
from data_api.runtime import get_runtime

router = APIRouter(responses=SNAPSHOT_RESPONSES)


@router.get("", response_model=list[Department], operation_id="getDirectory")
async def get_directory(
    response: Response,
    query: Annotated[
        str | None, Query(description="搜尋部門名稱、人員姓名或職稱；未提供或為空時回傳全部")
    ] = None,
    fuzzy: Annotated[bool, Query(description="是否進行模糊搜尋，若不啟用則必須完全符合")] = True,
):
    """
    查詢清華通訊錄。預設模糊搜尋，fuzzy=false 時須完全符合。
    部門名稱符合時回傳完整部門資料；
    僅人員姓名或職稱符合時，保留部門資料並只回傳符合的人員。
    無結果時回傳空陣列。
    資料來源：[清華通訊錄](https://tel.net.nthu.edu.tw/nthusearch/)
    """
    commit_hash, data = await get_runtime().departments.get_directory(query=query, fuzzy=fuzzy)
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
