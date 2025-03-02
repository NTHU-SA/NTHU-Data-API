from enum import Enum

from pydantic import BaseModel, Field


class LibraryName(str, Enum):
    mainlib = "mainlib"
    hslib = "hslib"
    nandalib = "nandalib"
    mainlib_moonlight_area = "mainlib_moonlight_area"


class LibraryNumberOfGoods(BaseModel):
    borrow_quantity: int = Field(..., description="已換證數量")
    remaining_18_quantity: int = Field(..., description="18歲以上成人剩餘換證數量")
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
