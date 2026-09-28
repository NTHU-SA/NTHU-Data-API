from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

from data_api.utils.schema import url_corrector


class LibraryRssImage(BaseModel):
    # url 使用 str 而非 HttpUrl，因為有些圖片的 url 並非合法的 url，例如: //www.lib.nthu.edu.tw/image/news/8/20230912.jpg
    url: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = Field(
        None, description="圖片網址"
    )
    title: Optional[str] = Field(None, description="圖片標題")
    link: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = Field(
        None, description="連結"
    )


class LibraryRssItem(BaseModel):
    guid: Optional[str] = Field(None, description="文章 id")
    category: Optional[str] = Field(None, description="文章分類")
    title: str = Field(..., description="文章標題")
    link: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = Field(
        None, description="文章連結"
    )
    pubDate: Optional[str] = Field(None, description="文章發布日期")
    description: str = Field(..., description="文章內容")
    author: Optional[str] = Field(None, description="文章作者")
    image: Optional[LibraryRssImage] = Field(None, description="文章圖片")


class LibraryRssData(BaseModel):
    title: Optional[str] = Field(None, description="電子報標題")
    link: Annotated[HttpUrl, BeforeValidator(url_corrector)] = Field(..., description="電子報網址")
    date: Optional[str] = Field(None, description="發布日期")


class LibraryRssType(str, Enum):
    news = "news"
    eresources = "eresources"
    exhibit = "exhibit"
    branches = "branches"


class LibraryCalendarId(str, Enum):
    main = "main"
    hss = "hss"
    nanda = "nanda"


class LibraryCalendar(BaseModel):
    id: LibraryCalendarId = Field(
        ..., description="行事曆 id：總圖(main)、人社分館(hss)、南大分館(nanda)"
    )
    name: Optional[str] = Field(None, description="行事曆名稱")
    description: Optional[str] = Field(None, description="行事曆說明")
    timezone: Optional[str] = Field(None, description="時區")
    url: HttpUrl = Field(..., description="Google 行事曆網址")


class LibraryCalendarEvent(BaseModel):
    id: str = Field(..., description="事件 id")
    title: str = Field(..., description="事件標題，例如開館時間或休館")
    description: Optional[str] = Field(None, description="事件說明")
    start: str = Field(
        ..., description="開始時間；全天事件為日期 (YYYY-MM-DD)，否則為 ISO 8601 時間"
    )
    end: str = Field(..., description="結束時間；全天事件的結束日期不包含在內 (iCal 慣例)")
    all_day: bool = Field(..., description="是否為全天事件")


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
