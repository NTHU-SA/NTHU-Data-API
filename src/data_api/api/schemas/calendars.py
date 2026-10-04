"""Published campus calendar schemas."""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Calendar(BaseModel):
    id: str = Field(..., description="行事曆 id，例如 academic、library-main")
    name: Optional[str] = Field(None, description="行事曆名稱")
    description: Optional[str] = Field(None, description="行事曆說明")
    timezone: Optional[str] = Field(None, description="時區")
    category: Optional[str] = Field(None, description="行事曆分類，例如 library")
    source: Optional[str] = Field(None, description="資料來源，例如 NTHU Library")
    url: Optional[HttpUrl] = Field(None, description="來源行事曆網址")


class CalendarEvent(BaseModel):
    id: str = Field(..., description="事件 id")
    title: str = Field(..., description="事件標題")
    description: Optional[str] = Field(None, description="事件說明")
    start: str = Field(
        ..., description="開始時間；全天事件為日期 (YYYY-MM-DD)，否則為 ISO 8601 當地時間"
    )
    end: str = Field(..., description="結束時間；結束日期或時間不包含在內 (iCal 慣例)")
    all_day: bool = Field(..., description="是否為全天事件")
