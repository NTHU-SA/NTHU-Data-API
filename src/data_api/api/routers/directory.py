"""Directory router."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from data_api.api.schemas.departments import Department
from data_api.domain.departments.services import departments_service

router = APIRouter()


@router.get("", response_model=list[Department], operation_id="getDirectory")
async def get_directory(
    response: Response,
    query: Annotated[
        str | None, Query(description="模糊搜尋部門名稱、人員姓名或職稱；未提供或為空時回傳全部")
    ] = None,
):
    """
    查詢清華通訊錄。部門名稱符合時回傳完整部門資料；
    僅人員姓名或職稱符合時，保留部門資料並只回傳符合的人員。
    無結果時回傳空陣列。
    資料來源：[清華通訊錄](https://tel.net.nthu.edu.tw/nthusearch/)
    """
    commit_hash, data = await departments_service.get_directory(query=query)
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
