from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class GoodjobData(BaseModel):
    title: str = Field(..., title="活動名稱")
    description: str = Field(..., title="活動描述")
    date: str = Field(..., title="活動日期")


class ArtsCenterData(BaseModel):
    title: str = Field(..., title="活動名稱")
    link: Optional[HttpUrl] = Field(..., title="連結")
    image: Optional[HttpUrl] = Field(..., title="圖片網址")
