"""Newsletters router."""

from fastapi import APIRouter, Query, Response

from data_api.api.schemas import newsletters as schemas
from data_api.api.schemas.responses import SNAPSHOT_RESPONSES
from data_api.runtime import get_runtime

router = APIRouter(responses=SNAPSHOT_RESPONSES)


@router.get("", response_model=list[schemas.NewsletterInfo], operation_id="getAllNewsletters")
async def get_all_newsletters(
    response: Response,
    name: str = Query(None, description="電子報名稱。請透過 `/newsletters/sources` 取得來源列表。"),
    title: str = Query(None, description="電子報文章標題關鍵字"),
    fuzzy: bool = Query(True, description="是否進行模糊搜尋，若不啟用則名稱必須完全符合"),
):
    """
    取得所有的電子報。
    資料來源：[國立清華大學電子報系統](https://newsletter.cc.nthu.edu.tw/nthu-list/index.php/zh/)
    """
    commit_hash, data = await get_runtime().newsletters.get_newsletters(
        name=name, title=title, fuzzy=fuzzy
    )
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/sources",
    response_model=list[schemas.NewsletterSource],
    operation_id="getNewsletterSources",
)
async def get_newsletter_sources(
    response: Response,
    name: str = Query(None, description="電子報名稱（完全符合）"),
):
    """
    取得電子報來源列表（不包含文章）。
    資料來源：[國立清華大學電子報系統](https://newsletter.cc.nthu.edu.tw/nthu-list/index.php/zh/)
    """
    commit_hash, data = await get_runtime().newsletters.get_newsletter_sources(name=name)
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
