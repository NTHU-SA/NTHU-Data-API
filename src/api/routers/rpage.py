from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

from src.utils.scraper import rpage_scraper


class RpageData(BaseModel):
    title: Optional[str] = Field(default=None, description="公告標題")
    date: Optional[str] = Field(default=None, description="公告日期")
    url: Optional[HttpUrl] = Field(default=None, description="公告網址")


router = APIRouter()


@router.get(
    "/{full_path:path}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "title": "更新112/11/6(一)~113/1/14(日)南大校區區間車時刻表",
                            "date": "2023-11-02 ",
                            "url": "https://affairs.site.nthu.edu.tw/p/406-1165-258110,r1065.php?Lang=zh-tw",
                        },
                        {
                            "title": "112/10/16(一)~113/1/13(六)校園公車時刻表",
                            "date": "2023-10-12 ",
                            "url": "https://affairs.site.nthu.edu.tw/p/406-1165-256804,r1065.php?Lang=zh-tw",
                        },
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[RpageData],
)
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
    return rpage_scraper.announcement(str(full_path))
