from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

from data_api.utils.schema import url_corrector


class NewsletterArticle(BaseModel):
    title: Optional[str] = Field(None, description="電子報標題")
    link: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = Field(
        None, description="電子報網址"
    )
    date: Optional[str] = Field(None, description="發布日期")


class NewsletterSource(BaseModel):
    name: str = Field(..., description="該電子報名稱")
    link: Annotated[HttpUrl, BeforeValidator(url_corrector)] = Field(
        ..., description="該電子報網址"
    )
    details: dict = Field(..., description="該電子報詳細資訊")


class NewsletterInfo(NewsletterSource):
    articles: list[NewsletterArticle] = Field(..., description="該電子報文章列表")
