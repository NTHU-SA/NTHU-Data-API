"""
Announcements router.

Handles HTTP endpoints for announcements.
"""

from fastapi import APIRouter, Query, Response

from data_api.api.schemas import announcements as schemas
from data_api.domain.announcements import services

router = APIRouter()


@router.get(
    "",
    response_model=list[schemas.AnnouncementDetail],
    operation_id="getAnnouncements",
)
@router.get(
    "/",
    response_model=list[schemas.AnnouncementDetail],
    operation_id="getAnnouncementsDeprecated",
    deprecated=True,
    description="已棄用，請改用 GET /announcements。查詢參數與回傳格式不變。",
)
async def get_announcements(
    response: Response,
    department: str = Query(
        None,
        description="部門名稱。請透過 `/announcements/sources` 的 department 欄位取得部門名稱。",
    ),
    title: str = Query(None, description="公告標題關鍵字"),
    language: schemas.AnnouncementLanguageOption = Query(None, description="語言篩選"),
    fuzzy: bool = Query(True, description="是否進行模糊搜尋，若不啟用則必須完全符合（不建議）"),
    url: str = Query(
        None,
        description="公告來源網址部分比對，忽略 http:// 與 https://，可輸入網域或含路徑的網址；不受 fuzzy 影響。",
    ),
):
    """
    取得校內每個處室的所有公告資訊。
    資料來源：各處室網站
    """
    if fuzzy:
        commit_hash, data = await services.announcements_service.fuzzy_search_announcements(
            department=department, title=title, language=language, url=url
        )
    else:
        commit_hash, data = await services.announcements_service.get_announcements(
            department=department, title=title, language=language, url=url
        )
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/lists/departments",
    response_model=list[str],
    operation_id="listAnnouncementDepartments",
    deprecated=True,
    description="已棄用，請改從 GET /announcements/sources 的 department 欄位取得部門名稱並去除重複值。",
)
async def list_announcement_departments(response: Response):
    """取得所有有公告的部門列表，保留舊版回應格式。"""
    commit_hash, data = await services.announcements_service.list_departments()
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/sources",
    response_model=list[schemas.AnnouncementSource],
    operation_id="getAnnouncementsList",
)
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
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
