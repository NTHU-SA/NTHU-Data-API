from fastapi import APIRouter

from src.api import schemas
from src.utils.scrapers import rpage_scraper

router = APIRouter()


@router.get("/bulletin/recruitment", response_model=list[schemas.resources.RssData])
async def get_bulletin_recruitment():
    """
    獲取清華公佈欄的徵才公告。
    """
    return rpage_scraper.get_announcement(
        "https://bulletin.site.nthu.edu.tw/p/403-1086-5075-1.php?Lang=zh-tw"
    )
