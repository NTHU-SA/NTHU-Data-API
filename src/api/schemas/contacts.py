from uuid import UUID

from pydantic import BaseModel, Field


class ContactRelativeNode(BaseModel):
    name: str = Field(..., description="父節點或子節點名稱")
    id: UUID = Field(..., description="父節點或子節點 id")


class ContactData(BaseModel):
    name: str = Field(..., description="姓名")
    ext: str = Field(..., description="分機")
    tel: str = Field(..., description="電話")
    fax: str = Field(..., description="傳真")
    email: str = Field(..., description="電子郵件")
    parents: list[ContactRelativeNode] = Field(..., description="父節點")
    children: list[ContactRelativeNode] = Field(..., description="子節點")


class ContactsData(BaseModel):
    id: UUID = Field(..., description="電話資料 id")
    data: ContactData = Field(..., description="電話資料")
    create_time: str = Field(..., description="建立時間")
    update_time: str = Field(..., description="更新時間")


class ContactSearchData(BaseModel):
    name: str = Field(..., description="要查詢誰的電話")
    max_result: int = Field(10, description="最多回傳幾筆資料")
