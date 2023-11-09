from doctest import Example
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from uuid import UUID

from ..models.contacts import Contact


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


router = APIRouter()
contact = Contact()


@router.get("/", response_model=list[ContactsData])
def get_all_contact():
    """
    取得所有電話資料。
    """
    result = contact.get_all()
    return result


@router.get("/{id}", response_model=ContactsData)
def get_contact(
    id: UUID = Path(
        ..., example="7e00db83-b407-4320-af55-0a1b1f5734ad", description="要查詢電話的 ID"
    )
):
    """
    使用電話 id 取得電話資料。
    """
    result = contact.get_by_id(id)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/searches/{name}", response_model=list[ContactsData])
def search_contact_by_get_method(
    name: str = Path(..., example="清華學院", description="要查詢誰的電話")
):
    """
    根據名字模糊搜尋電話。
    """
    result = contact.fuzzy_search(name)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    return result


@router.post("/searches", response_model=list[ContactsData])
def search_contact_by_post_method(search_data: ContactSearchData):
    """
    根據名字模糊搜尋電話。
    """
    result = contact.fuzzy_search(search_data.name)
    result = result[: search_data.max_result]
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    return result
