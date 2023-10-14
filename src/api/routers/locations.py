from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/locations",
    tags=["locations"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def getalllocation():
    try:
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/searches")
def searchlocation(query: str):
    result = []
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get("/{location}")
def getlocation(name: str):
    result = []
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")
