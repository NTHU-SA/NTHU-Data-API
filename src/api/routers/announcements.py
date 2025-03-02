import requests
from fastapi import APIRouter, HTTPException, Path

from src.api.schemas.announcements import AnnouncementDetail

router = APIRouter()
announcements_data = requests.get("https://data.nthusa.tw/announcements.json").json()


@router.get("/", response_model=list[AnnouncementDetail], summary="取得所有公告列表")
async def get_all_announcements():
    """
    取得所有公告資訊。
    """
    return announcements_data


@router.get("/department", response_model=list[str], summary="取得所有有公告的部門列表")
async def get_all_department():
    """
    取得所有有公告的部門列表。
    """
    department_list = set()
    for announcement in announcements_data:
        department_list.add(announcement["department"])
    return list(department_list)


@router.get(
    "/department/{name}",
    response_model=AnnouncementDetail,
    summary="取得特定部門的公告列表",
)
async def get_announcements_by_department(
    name: str = Path(..., description="部門名稱", example="清華公佈欄")
):
    """
    取得特定部門的公告資訊。
    """
    for announcement in announcements_data:
        if announcement["department"] == name:
            return announcement
    raise HTTPException(status_code=404, detail="Not found")
