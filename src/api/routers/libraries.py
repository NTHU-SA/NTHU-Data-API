from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field, HttpUrl

from src.utils.scraper import library_scraper


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


router = APIRouter()


@router.get("/space", response_model=List[LibrarySpace])
def get_library_space_data():
    """
    取得空間使用資訊。
    """
    return library_scraper.get_space_data()


@router.get("/lost_and_found")
def get_library_lost_and_found():
    """
    取得失物招領資訊。
    """
    return library_scraper.get_lost_and_found()


@router.get("/rss/{rss}", response_model=List[LibraryRssItem])
def get_library_rss_data(
    rss: LibraryRssType = Path(
        ...,
        description="RSS 類型：最新消息(news)、電子資源(eresources)、展覽及活動(exhibit)、南大與人社分館(branches)",
    )
):
    """
    取得指定RSS資料。
    """
    return library_scraper.get_rss_data(rss.value)


@router.get("/openinghours/{libaray_name}", response_model=LibraryOpeningHour)
def get_library_opening_hours(
    libaray_name: LibraryName = Path(
        ..., description="圖書館代號：總圖(mainlib)、人社圖書館(hslib)、南大圖書館(nandalib)"
    )
):
    """
    取得指定圖書館的開放時間。
    """
    return library_scraper.get_opening_hours(libaray_name)


@router.get("/goods", response_model=LibraryNumberOfGoods)
def get_library_number_of_goods() -> LibraryNumberOfGoods:
    """
    取得總圖換證數量資訊。
    """
    return library_scraper.get_number_of_goods()
