from fastapi import APIRouter, HTTPException

from ..models.lib import (
    get_opening_hours,
    get_number_of_goods,
    get_space_data,
    get_rss_data,
)

router = APIRouter(
    prefix="/lib",
    tags=["lib"],
    responses={404: {"description": "Not found"}},
)


@router.get("/openinghours/{lib}")
def openinghours(lib):
    try:
        content, code = get_opening_hours(lib)
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/goods")
def numberofgoods():
    try:
        content, code = get_number_of_goods()
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/space")
def spacedata():
    try:
        content, code = get_space_data()
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/rss/{rss}")
def rssdata(rss):
    try:
        content, code = get_rss_data(rss)
        if code != 200:
            raise HTTPException(status_code=code, detail="Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
