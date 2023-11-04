from enum import Enum
from typing import Optional
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, HttpUrl, Field

from ..models.lib import (
    get_opening_hours,
    get_number_of_goods,
    get_space_data,
    get_rss_data,
)


class Lib(str, Enum):
    mainlib = "mainlib"
    hslib = "hslib"
    nandalib = "nandalib"


class OpeningHours(BaseModel):
    library: Lib = Field(..., description="圖書館代號")
    date: str = Field(..., description="日期")
    start_time: str = Field(..., description="開館時間")
    end_time: str = Field(..., description="閉館時間")


class NumberOfGoods(BaseModel):
    borrow_quantity: str = Field(..., description="已換證數量")
    remaining_18_quantity: str = Field(..., description="18歲以上成人剩餘換證數量")
    remaining_15_18_quantity: str = Field(..., description="15~18歲青少年剩餘換證數量")


class Space(BaseModel):
    spacetype: int = Field(..., description="空間類型")
    spacetypename: str = Field(..., description="空間類型名稱")
    zoneid: str = Field(..., description="區域代號")
    zonename: str = Field(..., description="區域名稱")
    count: int = Field(..., description="空間剩餘數量")


class SpaceData(BaseModel):
    rescode: int = Field(..., description="回傳代碼")
    resmsg: str = Field(..., description="回傳訊息")
    rows: list[Space] = Field(..., description="各空間資料")


class Rss(str, Enum):
    rss_news = "rss_news"
    rss_eresources = "rss_eresources"
    rss_exhibit = "rss_exhibit"
    rss_branches = "rss_branches"


class Image(BaseModel):
    # url 使用 str 而非 HttpUrl，因為有些圖片的 url 並非合法的 url，例如: //www.lib.nthu.edu.tw/image/news/8/20230912.jpg
    url: str = Field(..., description="圖片網址")
    title: str = Field(..., description="圖片標題")
    link: Optional[HttpUrl] = Field(..., description="圖片連結")


class Item(BaseModel):
    guid: str = Field(..., description="文章 id")
    category: str = Field(..., description="文章分類")
    title: str = Field(..., description="文章標題")
    link: Optional[HttpUrl] = Field(..., description="文章連結")
    pubDate: str = Field(..., description="文章發布日期")
    description: str = Field(..., description="文章內容")
    author: str = Field(..., description="文章作者")
    image: Image = Field(..., description="文章圖片")


class RssData(BaseModel):
    title: str = Field(..., description="RSS 標題")
    link: Optional[HttpUrl] = Field(..., description="RSS 來源連結")
    description: str = Field(..., description="RSS 來源描述")
    language: str = Field(..., description="RSS 語言")
    pubDate: str = Field(..., description="RSS 發布日期")
    item: list[Item] = Field(..., description="RSS 文章列表")


router = APIRouter(
    prefix="/lib",
    tags=["lib"],
    responses={404: {"description": "Not found"}},
)


@router.get("/openinghours/{lib}", response_model=OpeningHours)
def openinghours(
    lib: Lib = Path(..., description="圖書館代號：總圖(mainlib)、人社圖書館(hslib)、南大圖書館(nandalib)")
):
    """
    取得指定圖書館的開放時間。
    """
    try:
        content, code = get_opening_hours(lib)
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/goods", response_model=NumberOfGoods)
def numberofgoods():
    """
    取得總圖換證數量資訊。
    """
    try:
        content, code = get_number_of_goods()
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/space", response_model=SpaceData)
def spacedata():
    """
    取得空間使用資訊。
    """
    try:
        content, code = get_space_data()
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/rss/{rss}", response_model=RssData)
def rssdata(
    rss: Rss = Path(
        ...,
        description="RSS 類型：最新消息(rss_news)、電子資源(rss_eresources)、展覽及活動(rss_exhibit)、南大與人社分館(rss_branches)",
    )
):
    """
    取得指定RSS資料。
    """
    try:
        content, code = get_rss_data(rss)
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
