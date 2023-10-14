from fastapi import APIRouter, HTTPException

from ..models.phones import Phone

router = APIRouter(
    prefix="/phones",
    tags=["phones"],
    responses={404: {"description": "Not found"}},
)

phone = Phone()


@router.get("/")
def getallphone():
    try:
        result = phone.all()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/searches")
def searchphone(query: str):
    result = phone.fuzz(query)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get("/{query}")
def getphone(query: str):
    result = phone.get(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")
