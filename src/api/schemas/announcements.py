from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

from src.utils.schema import url_corrector


class AnnouncementArticle(BaseModel):
    title: Optional[str] = Field(..., description="公告標題")
    link: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = Field(
        ..., description="公告連結"
    )
    date: Optional[str] = Field(None, description="公告日期 (YYYY-MM-DD)")


class AnnouncementDetail(BaseModel):
    title: str = Field(..., description="佈告欄標題")
    link: Annotated[HttpUrl, BeforeValidator(url_corrector)] = Field(
        ..., description="佈告欄連結"
    )
    language: str = Field(..., description="佈告欄語言")
    department: str = Field(..., description="發布部門")
    articles: list[AnnouncementArticle] = Field(..., description="公告列表")
