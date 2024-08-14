from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class RssImage(BaseModel):
    # url 使用 str 而非 HttpUrl，因為有些圖片的 url 並非合法的 url，例如: //www.lib.nthu.edu.tw/image/news/8/20230912.jpg
    url: str = Field(..., description="圖片網址")
    title: str = Field(..., description="圖片標題")
    link: Optional[HttpUrl] = Field(..., description="連結")


class RssItem(BaseModel):
    guid: str = Field(..., description="文章 id")
    category: str = Field(..., description="文章分類")
    title: str = Field(..., description="文章標題")
    link: Optional[HttpUrl] = Field(..., description="文章連結")
    pubDate: str = Field(..., description="文章發布日期")
    description: str = Field(..., description="文章內容")
    author: str = Field(..., description="文章作者")
    image: RssImage = Field(..., description="文章圖片")


class RssData(BaseModel):
    title: Optional[str] = Field(..., description="電子報標題")
    link: Optional[HttpUrl] = Field(..., description="電子報網址")
    date: Optional[str] = Field(..., description="發布日期")


class LibraryName(str, Enum):
    mainlib = "mainlib"
    hslib = "hslib"
    nandalib = "nandalib"


class LibraryOpeningHour(BaseModel):
    library: LibraryName = Field(..., description="圖書館代號")
    date: str = Field(..., description="日期")
    start_time: str = Field(..., description="開館時間")
    end_time: str = Field(..., description="閉館時間")
    message: str = Field(..., description="訊息")


class LibraryNumberOfGoods(BaseModel):
    borrow_quantity: str = Field(..., description="已換證數量")
    remaining_18_quantity: str = Field(..., description="18歲以上成人剩餘換證數量")
    remaining_15_18_quantity: str = Field(..., description="15~18歲青少年剩餘換證數量")


class LibraryRssType(str, Enum):
    news = "news"
    eresources = "eresources"
    exhibit = "exhibit"
    branches = "branches"


class LibrarySpace(BaseModel):
    spacetype: int = Field(..., description="空間類型")
    spacetypename: str = Field(..., description="空間類型名稱")
    zoneid: str = Field(..., description="區域代號")
    zonename: str = Field(..., description="區域名稱")
    count: int = Field(..., description="空間剩餘數量")


class LibraryLostAndFound(BaseModel):
    序號: str = Field(..., description="序號")
    拾獲時間: str = Field(..., description="拾獲日期")
    拾獲地點: str = Field(..., description="拾獲地點")
    描述: str = Field(..., description="物品描述")


class BulletinResourceTypeZH(str, Enum):
    行政公告 = "行政公告"
    校內徵才 = "校內徵才"
    校外徵才 = "校外徵才"
    招生公告 = "招生公告"
    藝文活動 = "藝文活動"
    學術活動 = "學術活動"
    學生活動 = "學生活動"
    其他公告 = "其他公告"
