from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from uuid import UUID

from ..models.phones import Phone


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
phone = Phone()


@router.get(
    "/",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "acfe50cc-3922-4acb-9fd2-4774520e82bc",
                            "data": {
                                "name": "台積電-國立清華大學聯合研發中心",
                                "ext": "34071",
                                "tel": "N/A",
                                "fax": "N/A",
                                "email": "N/A",
                                "parents": [
                                    {
                                        "name": "國際產學營運總中心",
                                        "id": "bc7fd10a-8d4f-42f2-8ae8-d065f94321be",
                                    }
                                ],
                                "children": [],
                            },
                            "create_time": "20231014T225508+0800",
                            "update_time": "20231014T225508+0800",
                        },
                        {
                            "...",
                        },
                    ]
                }
            }
        }
    },
    response_model=list[ContactsData],
)
def get_all_phone():
    """
    取得所有電話資料。
    """
    try:
        result = phone.get_all()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post(
    "/searches",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "acfe50cc-3922-4acb-9fd2-4774520e82bc",
                            "data": {
                                "name": "台積電-國立清華大學聯合研發中心",
                                "ext": "34071",
                                "tel": "N/A",
                                "fax": "N/A",
                                "email": "N/A",
                                "parents": [
                                    {
                                        "name": "國際產學營運總中心",
                                        "id": "bc7fd10a-8d4f-42f2-8ae8-d065f94321be",
                                    }
                                ],
                                "children": [],
                            },
                            "create_time": "20231014T225508+0800",
                            "update_time": "20231014T225508+0800",
                        },
                        {
                            "...",
                        },
                    ]
                }
            }
        }
    },
    response_model=list[ContactsData],
)
def search_phone(search_data: ContactSearchData):
    """
    根據名字模糊搜尋電話。
    """
    result = phone.fuzzy_search(search_data.name)
    result = result[: search_data.max_result]
    print(len(result))
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get(
    "/{id}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "id": "acfe50cc-3922-4acb-9fd2-4774520e82bc",
                        "data": {
                            "name": "台積電-國立清華大學聯合研發中心",
                            "ext": "34071",
                            "tel": "N/A",
                            "fax": "N/A",
                            "email": "N/A",
                            "parents": [
                                {
                                    "name": "國際產學營運總中心",
                                    "id": "bc7fd10a-8d4f-42f2-8ae8-d065f94321be",
                                }
                            ],
                            "children": [],
                        },
                        "create_time": "20231014T225508+0800",
                        "update_time": "20231014T225508+0800",
                    }
                }
            }
        }
    },
    response_model=ContactsData,
)
def get_phone(id: UUID = Path(..., description="要查詢電話的 id")):
    """
    使用電話 id 取得電話資料。
    """
    result = phone.get_by_id(id)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")


@router.get(
    "/searches/{name}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "acfe50cc-3922-4acb-9fd2-4774520e82bc",
                            "data": {
                                "name": "台積電-國立清華大學聯合研發中心",
                                "ext": "34071",
                                "tel": "N/A",
                                "fax": "N/A",
                                "email": "N/A",
                                "parents": [
                                    {
                                        "name": "國際產學營運總中心",
                                        "id": "bc7fd10a-8d4f-42f2-8ae8-d065f94321be",
                                    }
                                ],
                                "children": [],
                            },
                            "create_time": "20231014T225508+0800",
                            "update_time": "20231014T225508+0800",
                        },
                        {
                            "...",
                        },
                    ]
                }
            }
        }
    },
    response_model=list[ContactsData],
)
def search_phone(name: str = Path(..., description="要查詢誰的電話")):
    """
    根據名字模糊搜尋電話。
    """
    result = phone.fuzzy_search(name)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result
