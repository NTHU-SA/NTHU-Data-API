from fastapi import APIRouter, Path

from src.api import schemas
from src.utils.scrapers import rpage_scraper

router = APIRouter()

URL_PREFIX = "https://bulletin.site.nthu.edu.tw/p/403-1086-"
URL_POSTFIX = "-1.php?Lang=zh-tw"


@router.get("/zh/{type}", response_model=list[schemas.resources.RssData])
async def get_bulletin_resources_zh(
    type: schemas.resources.BulletinResourceTypeZH = Path(
        ..., example="行政公告", description="公告類型"
    ),
):
    """
    獲取清華公佈欄的資源。
    """
    index = {
        "行政公告": "5074",
        "校內徵才": "5075",
        "校外徵才": "5081",
        "招生公告": "5082",
        "藝文活動": "5083",
        "學術活動": "5084",
        "學生活動": "5085",
        "其他公告": "5086",
    }
    url = URL_PREFIX + index[type] + URL_POSTFIX
    return rpage_scraper.get_announcement(url)
