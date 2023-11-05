from enum import Enum
from typing import Optional
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, HttpUrl, Field

from ..models.librarys import (
    get_opening_hours,
    get_number_of_goods,
    get_space_data,
)

from src.utils.scraper import library_rss_scraper


class LibraryName(str, Enum):
    mainlib = "mainlib"
    hslib = "hslib"
    nandalib = "nandalib"


class LibraryOpeningHour(BaseModel):
    library: LibraryName = Field(..., description="圖書館代號")
    date: str = Field(..., description="日期")
    start_time: str = Field(..., description="開館時間")
    end_time: str = Field(..., description="閉館時間")


class LibraryNumberOfGoods(BaseModel):
    borrow_quantity: str = Field(..., description="已換證數量")
    remaining_18_quantity: str = Field(..., description="18歲以上成人剩餘換證數量")
    remaining_15_18_quantity: str = Field(..., description="15~18歲青少年剩餘換證數量")


class LibrarySpace(BaseModel):
    spacetype: int = Field(..., description="空間類型")
    spacetypename: str = Field(..., description="空間類型名稱")
    zoneid: str = Field(..., description="區域代號")
    zonename: str = Field(..., description="區域名稱")
    count: int = Field(..., description="空間剩餘數量")


class LibrarySpaceData(BaseModel):
    rescode: int = Field(..., description="回傳代碼")
    resmsg: str = Field(..., description="回傳訊息")
    rows: list[LibrarySpace] = Field(..., description="各空間資料")


class LibraryRssType(str, Enum):
    news = "news"
    eresources = "eresources"
    exhibit = "exhibit"
    branches = "branches"


class LibraryRssImage(BaseModel):
    # url 使用 str 而非 HttpUrl，因為有些圖片的 url 並非合法的 url，例如: //www.lib.nthu.edu.tw/image/news/8/20230912.jpg
    url: str = Field(..., description="圖片網址")
    title: str = Field(..., description="圖片標題")
    link: Optional[HttpUrl] = Field(..., description="圖片連結")


class LibraryRssItem(BaseModel):
    guid: str = Field(..., description="文章 id")
    category: str = Field(..., description="文章分類")
    title: str = Field(..., description="文章標題")
    link: Optional[HttpUrl] = Field(..., description="文章連結")
    pubDate: str = Field(..., description="文章發布日期")
    description: str = Field(..., description="文章內容")
    author: str = Field(..., description="文章作者")
    image: LibraryRssImage = Field(..., description="文章圖片")


class LibraryRssData(BaseModel):
    title: str = Field(..., description="RSS 標題")
    link: Optional[HttpUrl] = Field(..., description="RSS 來源連結")
    description: str = Field(..., description="RSS 來源描述")
    language: str = Field(..., description="RSS 語言")
    pubDate: str = Field(..., description="RSS 發布日期")
    item: list[LibraryRssItem] = Field(..., description="RSS 文章列表")


router = APIRouter()


@router.get("/openinghours/{lib}", response_model=LibraryOpeningHour)
def openinghours(
    lib: LibraryName = Path(
        ..., description="圖書館代號：總圖(mainlib)、人社圖書館(hslib)、南大圖書館(nandalib)"
    )
):
    """
    取得指定圖書館的開放時間。
    """
    data = get_opening_hours(lib)
    return data


@router.get("/goods", response_model=LibraryNumberOfGoods)
def numberofgoods():
    """
    取得總圖換證數量資訊。
    """
    goods = get_number_of_goods()
    return goods


@router.get("/space", response_model=LibrarySpaceData)
def spacedata():
    """
    取得空間使用資訊。
    """
    content = get_space_data()
    return content


@router.get("/rss/{rss}", response_model=LibraryRssData)
def rssdata(
    rss: LibraryRssType = Path(
        ...,
        description="RSS 類型：最新消息(rss_news)、電子資源(rss_eresources)、展覽及活動(rss_exhibit)、南大與人社分館(rss_branches)",
    )
):
    """
    取得指定RSS資料。
    """
    content = library_rss_scraper.get_rss_data(rss.value)
    return content
