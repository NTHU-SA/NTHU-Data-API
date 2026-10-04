"""Newsletters router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response

from data_api.api.schemas import newsletters as schemas
from data_api.domain.newsletters import services

router = APIRouter()


@router.get("", response_model=list[schemas.NewsletterInfo], operation_id="getAllNewsletters")
@router.get(
    "/",
    response_model=list[schemas.NewsletterInfo],
    operation_id="getAllNewslettersDeprecated",
    deprecated=True,
    description="已棄用，請改用 GET /newsletters。查詢參數與回傳格式不變。",
)
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
    commit_hash, data = await services.newsletters_service.get_newsletters(
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
    commit_hash, data = await services.newsletters_service.get_newsletter_sources(name=name)
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get(
    "/{newsletter_name}",
    response_model=schemas.NewsletterInfo,
    operation_id="getNewsletterByName",
    responses={404: {"description": "Newsletter not found"}},
    deprecated=True,
)
async def get_newsletter_by_name(
    response: Response,
    newsletter_name: Annotated[schemas.NewsletterName, Path()],
):
    """取得指定電子報的資訊。已棄用，請改用 `/newsletters?name=...&fuzzy=false`。"""
    commit_hash, data = await services.newsletters_service.get_newsletter_by_name(
        name=newsletter_name
    )
    if data is None:
        raise HTTPException(status_code=404, detail="電子報名稱不存在")

    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
