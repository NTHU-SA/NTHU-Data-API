from fastapi import APIRouter, Query
from thefuzz import fuzz

from src.api.schemas.announcements import AnnouncementArticle, AnnouncementDetail
from src.utils import nthudata

router = APIRouter()
ANNOUNCEMENTS_JSON = "announcements.json"
ANNOUNCEMENTS_LIST_JSON = "announcements_list.json"
FUZZY_SEARCH_THRESHOLD = 60


@router.get("/", response_model=list[AnnouncementDetail])
async def get_announcements(
    department: str = Query(None, description="部門名稱", example="清華公佈欄"),
):
    """
    取得校內每個處室的所有公告資訊。
    資料來源：各處室網站
    """
    _commit_hash, announcements_data = await nthudata.get(ANNOUNCEMENTS_JSON)
    if department:
        announcements_data = [
            announcement
            for announcement in announcements_data
            if announcement["department"] == department
        ]
    return announcements_data


@router.get("/lists", response_model=list[dict])
async def get_announcements_list(
    department: str = Query(None, description="部門名稱", example="清華公佈欄"),
):
    """
    取得校內每個處室的公告列表（不含文章內容）。
    資料來源：各處室網站
    """
    _commit_hash, announcements_list = await nthudata.get(ANNOUNCEMENTS_LIST_JSON)
    if department:
        announcements_list = [
            announcement
            for announcement in announcements_list
            if announcement["department"] == department
        ]
    return announcements_list


@router.get(
    "/search",
    response_model=list[AnnouncementArticle],
)
async def fuzzy_search_announcement_titles(
    query: str = Query(..., example="中研院", description="要查詢的公告"),
):
    """
    使用名稱模糊搜尋全部公告的標題。
    """
    _commit_hash, announcements_data = await nthudata.get(ANNOUNCEMENTS_JSON)
    tmp_results = []
    for announcement in announcements_data:
        articles = announcement.get("articles")
        if articles is None:
            continue
        for article in articles:
            similarity = fuzz.partial_ratio(query, article["title"])
            if similarity >= FUZZY_SEARCH_THRESHOLD:
                tmp_results.append(
                    (
                        similarity,  # 儲存相似度
                        article,
                    )
                )
    tmp_results.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in tmp_results]


@router.get("/lists/departments", response_model=list[str])
async def list_announcement_departments():
    """
    取得所有有公告的部門列表。
    """
    _commit_hash, announcements_list = await nthudata.get(ANNOUNCEMENTS_LIST_JSON)
    departments = {announcement["department"] for announcement in announcements_list}
    return sorted(departments)
