from fastapi import APIRouter, HTTPException
from ..models.locations import Location

router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    responses={404: {"description": "Not found"}},
)

location = Location()


@router.get("/")
def getalllocation():
    try:
        result = location.get_all()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/searches")
def searchlocation(query: str, max_result: int = 10):
    result = location.fuzzy_search(query)
    result = result[:max_result]
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get("/{query}")
def getlocation(query: str):
    result = location.get_by_id(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/searches/{query}")
def searchlocation(query: str):
    result = location.fuzzy_search(query)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result
