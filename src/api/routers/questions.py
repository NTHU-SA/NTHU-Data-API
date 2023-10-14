from fastapi import APIRouter, HTTPException

from ..models.questions import Question

router = APIRouter(
    prefix="/questions",
    tags=["questions"],
    responses={404: {"description": "Not found"}},
)

question = Question()


@router.get("/")
def getallquestion():
    try:
        result = question.all()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/searches")
def searchquestion(query: str):
    result = question.fuzz(query)
    if result == []:
        raise HTTPException(status_code=404, detail="Not found")
    else:
        return result


@router.get("/{query}")
def getquestion(query: str):
    result = question.get(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Not found")
