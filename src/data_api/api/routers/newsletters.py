"""Newsletters router."""

from fastapi import APIRouter, HTTPException, Path, Response

from data_api.api.schemas import newsletters as schemas
from data_api.domain.newsletters import services

router = APIRouter()


@router.get("/", response_model=list[schemas.NewsletterInfo])
async def get_all_newsletters(response: Response):
    """
    取得所有的電子報。
    資料來源：[國立清華大學電子報系統](https://newsletter.cc.nthu.edu.tw/nthu-list/index.php/zh/)
    """
    commit_hash, data = await services.newsletters_service.get_all_newsletters()
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data


@router.get("/{newsletter_name}", response_model=schemas.NewsletterInfo)
async def get_newsletter_by_name(
    response: Response,
    newsletter_name: schemas.NewsletterName = Path(
        ..., example="國立清華大學學生會電子報"
    ),
):
    """取得指定電子報的資訊。"""
    commit_hash, data = await services.newsletters_service.get_newsletter_by_name(
        name=newsletter_name
    )
    if commit_hash is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    if data is None:
        raise HTTPException(status_code=404, detail="電子報名稱不存在")

    response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
