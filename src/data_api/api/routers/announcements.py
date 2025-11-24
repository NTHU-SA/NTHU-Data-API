"""
Announcements router.

Handles HTTP endpoints for announcements.
"""

from fastapi import APIRouter, HTTPException, Query, Response

from data_api.api.schemas import announcements as schemas
from data_api.domain.announcements import services

router = APIRouter()


@router.get(
    "/",
    response_model=list[schemas.AnnouncementDetail],
    operation_id="getAnnouncements",
)
async def get_announcements(
    response: Response,
    department: str = Query(
        None,
        description="部門名稱。請透過 `/announcements/lists/departments` 取得完整列表。",
    ),
    title: str = Query(None, description="公告標題關鍵字"),
    language: schemas.AnnouncementLanguageOption = Query(None, description="語言篩選"),
    fuzzy: bool = Query(False, description="是否進行模糊搜尋"),
):
    """
    取得校內每個處室的所有公告資訊。
    資料來源：各處室網站
    """
    if fuzzy:
        commit_hash, data = (
            await services.announcements_service.fuzzy_search_announcements(
                department=department, title=title, language=language
            )
        )
    else:
        commit_hash, data = await services.announcements_service.get_announcements(
            department=department, title=title, language=language
        )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get("/sources", response_model=list[dict], operation_id="getAnnouncementsList")
async def get_announcements_list(
    response: Response,
    department: str = Query(None, description="部門名稱"),
):
    """
    取得公告列表（不包含文章內容）。
    資料來源：各處室網站
    """
    commit_hash, data = await services.announcements_service.get_announcements_list(
        department=department
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/lists/departments",
    response_model=list[str],
    operation_id="listAnnouncementDepartments",
)
async def list_announcement_departments(response: Response):
    """取得所有有公告的部門列表。"""
    commit_hash, data = await services.announcements_service.list_departments()
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
