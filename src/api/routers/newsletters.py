import json

from fastapi import APIRouter, HTTPException, Path
from pydantic import HttpUrl

from src.api import schemas
from src.utils.scraper import newsletter_scraper

router = APIRouter()


@router.get("/", response_model=list[schemas.newsletter.NewsletterInfo])
def get_all_newsletters():
    """
    取得所有的電子報。
    """
    return newsletter_scraper.get_all_newsletters_list()


@router.get("/{newsletter_name}", response_model=list[schemas.resources.RssItem])
def get_newsletter_by_name(
    newsletter_name: schemas.newsletter.NewsletterName = Path(
        ..., example="國立清華大學學生會電子報", description="抓取的電子報名稱"
    )
):
    """
    透過電子報名稱取得指定的電子報列表。
    """
    with open("data/newsletter_list.json", "r", encoding="utf-8") as f:
        data = f.read()
    data = json.loads(data)
    newsletter_link = None
    for newsletter in data:
        if newsletter["name"] == newsletter_name:
            newsletter_link = newsletter["link"]
            break
    if newsletter_link is None:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    return newsletter_scraper.get_selected_newsletter_list(newsletter_link)


@router.get(
    "/paths/{newsletter_link:path}", response_model=list[schemas.resources.RssData]
)
def get_newsletter_by_link(
    newsletter_link: HttpUrl = Path(
        ...,
        example="https://newsletter.cc.nthu.edu.tw/nthu-list/index.php/zh/home-zh-tw/listid-44-",
        description="抓取的電子報網址",
    )
):
    """
    透過電子報網址取得指定的電子報列表。
    """
    return newsletter_scraper.get_selected_newsletter_list(str(newsletter_link))
