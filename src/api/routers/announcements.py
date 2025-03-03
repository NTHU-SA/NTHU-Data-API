from fastapi import APIRouter, HTTPException, Path

from src.api.schemas.announcements import AnnouncementDetail
from src.utils import nthudata

router = APIRouter()
json_path = "announcements.json"


@router.get("/", response_model=list[AnnouncementDetail], summary="取得所有公告列表")
async def get_all_announcements():
    """
    取得所有公告資訊。
    """
    _commit_hash, announcements_data = await nthudata.get(json_path)
    return announcements_data


@router.get(
    "/departments", response_model=list[str], summary="取得所有有公告的部門列表"
)
async def get_all_department():
    """
    取得所有有公告的部門列表。
    """
    _commit_hash, announcements_data = await nthudata.get(json_path)
    departments = set()
    for announcement in announcements_data:
        departments.add(announcement["department"])
    return list(departments)


@router.get(
    "/departments/{name}",
    response_model=list[AnnouncementDetail],
    summary="取得特定部門的公告列表",
)
async def get_announcements_by_department(
    name: str = Path(..., description="部門名稱", example="清華公佈欄")
):
    """
    取得特定部門的公告資訊。
    """
    _commit_hash, announcements_data = await nthudata.get(json_path)
    announcements = []
    for announcement in announcements_data:
        if announcement["department"] == name:
            announcements.append(announcement)
    if announcements:
        return announcements
    raise HTTPException(status_code=404, detail="部門名稱不存在")
