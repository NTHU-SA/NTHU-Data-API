from typing import Optional

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field, HttpUrl

from src.api import schemas
from src.utils.scraper import rpage_scraper

router = APIRouter()


@router.get("/{full_path:path}", response_model=list[schemas.resources.RssData])
def get_rpage_data(
    full_path: HttpUrl = Path(
        ...,
        example="https://bulletin.site.nthu.edu.tw/p/403-1086-5081-1.php?Lang=zh-tw",
        description="Rpage 完整公告網址",
    )
):
    """
    爬取指定 Rpage 公告的內容。
    """
    return rpage_scraper.get_announcement(str(full_path))
