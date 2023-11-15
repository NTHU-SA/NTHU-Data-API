from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from src.api import schemas
from src.api.models.contacts import Contact

router = APIRouter()
contact = Contact()


@router.get("/", response_model=list[schemas.contacts.ContactsData])
def get_all_contact():
    """
    取得所有電話資料。
    """
    result = contact.get_all()
    return result


@router.get("/{id}", response_model=schemas.contacts.ContactsData)
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


@router.get("/searches/{name}", response_model=list[schemas.contacts.ContactsData])
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


@router.post("/searches", response_model=list[schemas.contacts.ContactsData])
def search_contact_by_post_method(search_data: schemas.contacts.ContactSearchData):
    """
    根據名字模糊搜尋電話。
    """
    result = contact.fuzzy_search(search_data.name)
    result = result[: search_data.max_result]
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    return result
