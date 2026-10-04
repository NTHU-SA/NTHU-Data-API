from fastapi import APIRouter, HTTPException, Path, Response

from data_api.api.errors import service_errors
from data_api.api.schemas.errors import LIVE_ERROR_RESPONSES
from data_api.api.schemas.libraries import (
    LibraryLostAndFound,
    LibraryRssItem,
    LibraryRssType,
    LibrarySpace,
)
from data_api.domain.libraries.services import libraries_service

router = APIRouter()


@router.get(
    "/space",
    response_model=list[LibrarySpace],
    operation_id="getLibrarySpaceAvailability",
    responses=LIVE_ERROR_RESPONSES,
)
async def get_library_space_availability():
    """
    取得圖書館空間使用資訊。
    資料來源：[圖書館空間預約系統](https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx)
    """
    with service_errors():
        return await libraries_service.get_space_availability()


@router.get(
    "/lost_and_found",
    response_model=list[LibraryLostAndFound],
    operation_id="getLibraryLostAndFoundItems",
    responses=LIVE_ERROR_RESPONSES,
    deprecated=True,
    description="已棄用，請改用 `GET /libraries/lost-and-found`。",
)
@router.get(
    "/lost-and-found",
    response_model=list[LibraryLostAndFound],
    operation_id="getLibraryLostAndFound",
    responses=LIVE_ERROR_RESPONSES,
)
async def get_library_lost_and_found_items():
    """
    取得圖書館失物招領資訊。
    資料來源：[圖書館失物招領系統](https://adage.lib.nthu.edu.tw/find)
    """
    with service_errors():
        return await libraries_service.get_lost_and_found_items()


@router.get(
    "/rss/{rss_type}",
    response_model=list[LibraryRssItem],
    operation_id="getLibraryRssData",
    responses={404: {"description": "RSS feed not found"}},
)
async def get_library_rss_data(
    response: Response,
    rss_type: LibraryRssType = Path(
        ...,
        description="RSS 類型：最新消息(news)、電子資源(eresources)、展覽及活動(exhibit)、南大與人社分館(branches)",
    ),
):
    """
    取得指定圖書館的 RSS 資料。
    資料來源：[圖書館官網 RSS](https://www.lib.nthu.edu.tw/bulletin/RSS/index.html)
    """
    commit_hash, items = await libraries_service.get_rss_items(rss_type.value)
    if items is None:
        raise HTTPException(status_code=404, detail="找不到 RSS 資料")

    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return items
