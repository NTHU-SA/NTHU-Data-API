"""Libraries API schemas."""
from enum import Enum
from pydantic import BaseModel, Field

class LibraryName(str, Enum):
    """Library names."""
    總圖書館 = "總圖書館"
    人社分館 = "人社分館"
    數學分館 = "數學分館"

class LibraryOpeningHours(BaseModel):
    day: str = Field(..., description="星期")
    time: str = Field(..., description="開館時間")

class LibraryInfo(BaseModel):
    name: str = Field(..., description="圖書館名稱")
    opening_hours: list[LibraryOpeningHours] = Field(..., description="開館時間")
