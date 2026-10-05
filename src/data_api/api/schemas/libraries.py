from enum import Enum
from typing import Annotated, Optional
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

from data_api.utils.schema import url_corrector


def rss_image_url_corrector(value: object) -> object:
    value = url_corrector(value)
    if isinstance(value, str):
        parts = urlsplit(value)
        return urlunsplit(parts._replace(path=parts.path.replace(" ", "%20")))
    return value


class LibraryRssImage(BaseModel):
    url: Optional[Annotated[HttpUrl, BeforeValidator(rss_image_url_corrector)]] = Field(
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
    link: Optional[str] = Field(None, description="文章連結文字，可能包含多個網址")
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
