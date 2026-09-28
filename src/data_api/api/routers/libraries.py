import json
import re
import ssl
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
import truststore
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Path, Query, Response

from data_api.api.schemas.libraries import (
    LibraryCalendar,
    LibraryCalendarEvent,
    LibraryCalendarId,
    LibraryLostAndFound,
    LibraryRssItem,
    LibraryRssType,
    LibrarySpace,
)
from data_api.domain.libraries.services import libraries_service

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}
SERVICE_UNAVAILABLE = "Service temporarily unavailable"

router = APIRouter()

ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


@router.get(
    "/space",
    response_model=list[LibrarySpace],
    operation_id="getLibrarySpaceAvailability",
)
async def get_library_space_availability():
    """
    取得圖書館空間使用資訊。
    資料來源：[圖書館空間預約系統](https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx)
    """
    url = "https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx"
    try:
        async with httpx.AsyncClient(verify=ctx) as client:  # 圖書館的 RSS 使用了特別的憑證(TWCA)
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            data = response.json()

            if data.get("resmsg") != "成功":
                raise HTTPException(status_code=404, detail="找不到空間資料")
            return data["rows"]
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"擷取空間資料失敗: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"解析空間資料失敗: {e}")


@router.get(
    "/lost_and_found",
    response_model=list[LibraryLostAndFound],
    operation_id="getLibraryLostAndFoundItems",
)
async def get_library_lost_and_found_items():
    """
    取得圖書館失物招領資訊。
    資料來源：[圖書館失物招領系統](https://adage.lib.nthu.edu.tw/find)
    """
    date_end = datetime.now()
    date_start = date_end - timedelta(days=6 * 30)

    post_data = {
        "place": "0",
        "date_start": date_start.strftime("%Y-%m-%d"),
        "date_end": date_end.strftime("%Y-%m-%d"),
        "catalog": "ALL",
        "keyword": "",
        "SUMIT": "送出",
    }
    url = "https://adage.lib.nthu.edu.tw/find/search_it.php"

    try:
        async with httpx.AsyncClient(verify=ctx) as client:
            response = await client.post(url, data=post_data, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if not table:
                return []

            table_rows = table.find_all("tr")
            if not table_rows:
                return []

            # 提取表格標題
            table_title = [td.text.strip() for td in table_rows[0].find_all("td")]

            # 解析表格行
            rows_data = []
            for row in table_rows[1:]:
                cells = [re.sub(r"\s+", " ", td.text.strip()) for td in row.find_all("td")]
                if len(cells) == len(table_title):
                    rows_data.append(dict(zip(table_title, cells)))

            return rows_data
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"擷取失物招領資料失敗: {e}")
    except AttributeError:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失物招領資料失敗: {e}")


@router.get(
    "/rss/{rss_type}",
    response_model=list[LibraryRssItem],
    operation_id="getLibraryRssData",
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


CALENDAR_ID_PATH = Path(..., description="行事曆 id：總圖(main)、人社分館(hss)、南大分館(nanda)")


@router.get(
    "/calendars",
    response_model=list[LibraryCalendar],
    operation_id="getAllLibraryCalendars",
)
async def get_all_library_calendars(response: Response):
    """
    取得所有圖書館開館時間行事曆（不含事件）。
    資料來源：[圖書館開放時間](https://www.lib.nthu.edu.tw/use/hours.html)
    """
    commit_hash, calendars = await libraries_service.get_all_calendars()
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return calendars


@router.get(
    "/calendars/{calendar_id}",
    response_model=LibraryCalendar,
    operation_id="getLibraryCalendar",
)
async def get_library_calendar(
    response: Response,
    calendar_id: LibraryCalendarId = CALENDAR_ID_PATH,
):
    """取得指定行事曆的資訊（不含事件）。"""
    commit_hash, calendar = await libraries_service.get_calendar(calendar_id.value)
    if calendar is None:
        raise HTTPException(status_code=404, detail="找不到行事曆")

    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return calendar


@router.get(
    "/calendars/{calendar_id}/events",
    response_model=list[LibraryCalendarEvent],
    operation_id="searchLibraryCalendarEvents",
)
async def search_library_calendar_events(
    response: Response,
    calendar_id: LibraryCalendarId = CALENDAR_ID_PATH,
    start: Optional[date] = Query(
        None, description="只回傳在此日期（含）之後仍進行中的事件，格式 YYYY-MM-DD"
    ),
    end: Optional[date] = Query(
        None, description="只回傳在此日期（含）之前開始的事件，格式 YYYY-MM-DD"
    ),
    keyword: Optional[str] = Query(None, description="在標題與說明中搜尋的關鍵字，例如：閉館"),
    limit: int = Query(100, ge=1, le=1000, description="最多回傳筆數"),
    offset: int = Query(0, ge=0, description="略過的筆數，用於分頁"),
):
    """
    查詢指定行事曆的事件，依開始時間排序。
    符合條件的總筆數會放在 `X-Total-Count` header。

    例如查詢總圖今天的開館時間：`/libraries/calendars/main/events?start=2026-10-01&end=2026-10-01`
    """
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start 不可晚於 end")

    commit_hash, events = await libraries_service.search_calendar_events(
        calendar_id.value, start=start, end=end, keyword=keyword
    )
    if events is None:
        raise HTTPException(status_code=404, detail="找不到行事曆")

    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    response.headers["X-Total-Count"] = str(len(events))
    return events[offset : offset + limit]


@router.get(
    "/calendars/{calendar_id}/events/{event_id}",
    response_model=LibraryCalendarEvent,
    operation_id="getLibraryCalendarEvent",
)
async def get_library_calendar_event(
    response: Response,
    calendar_id: LibraryCalendarId = CALENDAR_ID_PATH,
    event_id: str = Path(..., description="事件 id"),
):
    """取得指定行事曆中的單一事件。"""
    commit_hash, event = await libraries_service.get_calendar_event(calendar_id.value, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="找不到事件")

    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return event
