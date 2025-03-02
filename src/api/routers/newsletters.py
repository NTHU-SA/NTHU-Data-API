import requests
from fastapi import APIRouter, HTTPException, Path

from src.api.schemas.newsletters import NewsletterInfo, NewsletterName

router = APIRouter()

newsletter_data = requests.get("https://data.nthusa.tw/newsletters.json").json()


@router.get("/", response_model=list[NewsletterInfo])
def get_all_newsletters():
    """
    取得所有的電子報。
    """
    return newsletter_data


@router.get("/{newsletter_name}", response_model=NewsletterInfo)
def get_newsletter_by_name(
    newsletter_name: NewsletterName = Path(
        ..., example="國立清華大學學生會電子報", description="抓取的電子報名稱"
    )
):
    """
    透過電子報名稱取得指定的電子報列表。
    """
    for newsletter in newsletter_data:
        if newsletter["name"] == newsletter_name:
            return newsletter
    raise HTTPException(status_code=404, detail="電子報名稱不存在")
