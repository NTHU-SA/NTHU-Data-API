from fastapi import APIRouter, HTTPException, Path
from pydantic import HttpUrl

from ..models.rpage import Rpage

router = APIRouter(
    prefix="/rpage",
    tags=["rpage"],
    responses={404: {"description": "Not found"}},
)

rpage = Rpage()


@router.get(
    "/{full_path:path}",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "title": "更新112/11/6(一)~113/1/14(日)南大校區區間車時刻表",
                            "date": "2023-11-02 ",
                            "url": "https://affairs.site.nthu.edu.tw/p/406-1165-258110,r1065.php?Lang=zh-tw",
                        },
                        {
                            "title": "112/10/16(一)~113/1/13(六)校園公車時刻表",
                            "date": "2023-10-12 ",
                            "url": "https://affairs.site.nthu.edu.tw/p/406-1165-256804,r1065.php?Lang=zh-tw",
                        },
                        {
                            "...",
                        },
                    ]
                },
            },
        },
    },
)
def get_rpage_data(full_path: HttpUrl = Path(..., description="Rpage 完整公告網址")):
    """
    爬取指定 Rpage 公告的內容。
    """
    try:
        content, code = rpage.crawler(full_path)
        if content == []:
            raise HTTPException(status_code=404, detail="Not found")
        elif code != 200:
            raise HTTPException(status_code=code, detail="Server Error")
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
