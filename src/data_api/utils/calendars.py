"""Shared calendar date and keyword filtering."""

from datetime import date, datetime, time, timedelta
from typing import Optional


def get_event_date_range(event: dict) -> tuple[date, date]:
    """
    Return the first and last day (both inclusive) an event covers.

    All-day events use an exclusive end date (iCal convention). Timed events
    use the local dates in the published timestamps.
    """
    first_day = date.fromisoformat(event["start"][:10])
    if event["all_day"]:
        last_day = date.fromisoformat(event["end"][:10]) - timedelta(days=1)
    else:
        end = datetime.fromisoformat(event["end"])
        last_day = end.date()
        # An event ending exactly at midnight does not cover the next day.
        if end.time() == time(0) and last_day > first_day:
            last_day -= timedelta(days=1)
    return first_day, max(first_day, last_day)


def filter_calendar_events(
    events: list[dict],
    start: Optional[date] = None,
    end: Optional[date] = None,
    keyword: Optional[str] = None,
) -> list[dict]:
    """Keep events that overlap [start, end] and contain keyword in title or description."""
    keyword = keyword.strip().lower() if keyword else None
    results = []
    for event in events:
        first_day, last_day = get_event_date_range(event)
        if start and last_day < start:
            continue
        if end and first_day > end:
            continue
        if keyword:
            text = f"{event['title']}\n{event.get('description') or ''}".lower()
            if keyword not in text:
                continue
        results.append(event)
    return results
