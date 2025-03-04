from fastapi import APIRouter, Query
from thefuzz import fuzz

from src.api.schemas.announcements import AnnouncementArticle, AnnouncementDetail
from src.utils import nthudata

router = APIRouter()
json_path = "announcements.json"


@router.get("/", response_model=list[AnnouncementDetail])
async def get_all_announcements(
    department: str = Query(None, description="部門名稱", example="清華公佈欄"),
):
    """
    取得校內每個處室的所有公告資訊。
    """
    _commit_hash, announcements_data = await nthudata.get(json_path)
    if department:
        announcements_data = [
            announcement
            for announcement in announcements_data
            if announcement["department"] == department
        ]
    return announcements_data


@router.get("/departments", response_model=list[str])
async def get_all_departments():
    """
    取得所有有公告的部門列表。
    """
    _commit_hash, announcements_data = await nthudata.get(json_path)
    departments = set()
    for announcement in announcements_data:
        departments.add(announcement["department"])
    return list(departments)


@router.get(
    "/search",
    response_model=list[AnnouncementArticle],
)
async def search_announcement(
    query: str = Query(..., example="中研院", description="要查詢的公告"),
):
    """
    使用名稱模糊搜尋全部公告的標題。
    """
    _commit_hash, announcements_data = await nthudata.get(json_path)
    tmp_results = []
    for announcement in announcements_data:
        articles = announcement.get("articles")
        if articles is None:
            continue
        for article in articles:
            similarity = fuzz.partial_ratio(query, article["title"])
            if similarity >= 60:
                tmp_results.append(
                    (
                        similarity,  # 儲存相似度
                        article,
                    )
                )
    tmp_results.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in tmp_results]
