from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class EventData(BaseModel):
    title: Optional[str] = Field(None, description="活動標題")
    description: Optional[str] = Field(None, description="活動描述")
    link: Optional[HttpUrl] = Field(None, description="活動網址")
    image: Optional[HttpUrl] = Field(None, description="活動圖片")
    unix_timestamp: Optional[int] = Field(None, description="活動發布日期")
    author: Optional[str] = Field(None, description="活動發布者")
