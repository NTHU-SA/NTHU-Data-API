"""Campus calendar endpoints."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, Response

from data_api.api.schemas.calendars import Calendar, CalendarEvent
from data_api.domain.calendars.services import calendars_service

router = APIRouter()

CALENDAR_ID_PATH = Path(
    ..., description="行事曆 id，可由 /calendars 取得，例如 academic、library-main"
)


@router.get("", response_model=list[Calendar], operation_id="getAllCalendars")
@router.get(
    "/",
    response_model=list[Calendar],
    operation_id="getAllCalendarsDeprecated",
    deprecated=True,
    description="已棄用，請改用 GET /calendars。回傳格式不變。",
)
async def get_all_calendars(response: Response):
    """
    取得所有校園行事曆的資訊（不含事件）。
    包含校級與圖書館開館時間行事曆。
    資料來源：[清華校園資料](https://data.nthusa.tw/calendars.json)、
    [圖書館行事曆](https://data.nthusa.tw/libraries/calendars.json)
    """
    commit_hash, calendars = await calendars_service.get_all_calendars()
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return calendars


@router.get(
    "/{calendar_id}",
    response_model=Calendar,
    operation_id="getCalendar",
    responses={404: {"description": "Calendar not found"}},
)
async def get_calendar(response: Response, calendar_id: str = CALENDAR_ID_PATH):
    """取得指定行事曆的資訊（不含事件）。"""
    commit_hash, calendar = await calendars_service.get_calendar(calendar_id)
    if calendar is None:
        raise HTTPException(status_code=404, detail="找不到行事曆")
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return calendar


@router.get(
    "/{calendar_id}/events",
    response_model=list[CalendarEvent],
    operation_id="searchCalendarEvents",
    responses={
        400: {"description": "Start date must not follow end date"},
        404: {"description": "Calendar not found"},
    },
)
async def search_calendar_events(
    response: Response,
    calendar_id: str = CALENDAR_ID_PATH,
    start: Optional[date] = Query(
        None, description="只回傳在此日期（含）之後仍進行中的事件，格式 YYYY-MM-DD"
    ),
    end: Optional[date] = Query(
        None, description="只回傳在此日期（含）之前開始的事件，格式 YYYY-MM-DD"
    ),
    keyword: Optional[str] = Query(
        None, description="在標題與說明中搜尋的關鍵字，不區分大小寫，不使用正規表示式"
    ),
    limit: int = Query(100, ge=1, le=1000, description="最多回傳筆數"),
    offset: int = Query(0, ge=0, description="略過的筆數，用於分頁"),
):
    """
    查詢與指定日期區間重疊的事件，依開始時間、事件 id 排序。

    日期採用來源行事曆的當地日期，區間包含首尾兩日，可省略任一邊界。
    全天事件的結束日期不包含在內；恰好於午夜結束的事件不涵蓋隔日。
    所有篩選條件以 AND 結合，分頁前的符合筆數放在 `X-Total-Count` header。

    例如：`/calendars/academic/events?start=2026-10-01&end=2026-10-31`
    """
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start 不可晚於 end")
    commit_hash, events = await calendars_service.search_calendar_events(
        calendar_id, start=start, end=end, keyword=keyword
    )
    if events is None:
        raise HTTPException(status_code=404, detail="找不到行事曆")
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    response.headers["X-Total-Count"] = str(len(events))
    return events[offset : offset + limit]


@router.get(
    "/{calendar_id}/events/{event_id}",
    response_model=CalendarEvent,
    operation_id="getCalendarEvent",
    responses={404: {"description": "Calendar event not found"}},
)
async def get_calendar_event(
    response: Response,
    calendar_id: str = CALENDAR_ID_PATH,
    event_id: str = Path(..., description="事件 id"),
):
    """取得指定行事曆中的單一事件。"""
    commit_hash, event = await calendars_service.get_calendar_event(calendar_id, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="找不到事件")
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return event
