from fastapi import APIRouter, HTTPException

from ..models.rpage import Rpage

router = APIRouter(
    prefix="/rpage",
    tags=["rpage"],
    responses={404: {"description": "Not found"}},
)

rpage = Rpage()


@router.get("/")
def rpage404():
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/{full_path:path}")
def getrpage(full_path: str):
    try:
        content, code = rpage.crawler(full_path)
        if content == []:
            raise HTTPException(status_code=404, detail="Not found")
        elif code != 200:
            raise HTTPException(status_code=code, detail="Server Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
