from fastapi import APIRouter, HTTPException
from ..models.phones import Phone

router = APIRouter(
    prefix="/phones",
    tags=["phones"],
    responses={404: {"description": "Not found"}},
)

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
)
def get_all_phone():
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
)
def search_phone(query: str, max_result: int = 10):
    result = phone.fuzzy_search(query)
    result = result[:max_result]
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get(
    "/{query}",
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
)
def get_phone(query: str):
    result = phone.get_by_id(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")


@router.get(
    "/searches/{query}",
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
)
def search_phone(query: str):
    result = phone.fuzzy_search(query)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result
