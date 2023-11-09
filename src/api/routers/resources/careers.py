from fastapi import APIRouter

from src.utils.scraper import rpage_scraper

router = APIRouter()


@router.get("/bulletin/recruitment")
async def get_bulletin_recruitment():
    """
    獲取清華公佈欄的徵才公告。
    """
    return rpage_scraper.announcement(
        "https://bulletin.site.nthu.edu.tw/p/403-1086-5075-1.php?Lang=zh-tw"
    )
