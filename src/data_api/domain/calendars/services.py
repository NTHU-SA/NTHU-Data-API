"""Campus calendar queries backed by the shared dataset snapshot."""

from datetime import date
from typing import Optional

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.utils.calendars import filter_calendar_events

JSON_PATH = "calendars.json"


class CalendarsService:
    async def get_all_calendars(self) -> tuple[Optional[str], list[dict]]:
        """Get calendar metadata without events."""
        commit_hash, calendars = await self._get_data()
        return commit_hash, [
            {key: value for key, value in calendar.items() if key != "events"}
            for calendar in calendars
        ]

    async def _get_data(self) -> tuple[Optional[str], list[dict]]:
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")
        return result

    async def get_calendar(self, calendar_id: str) -> tuple[Optional[str], Optional[dict]]:
        """Get one calendar, including its events."""
        commit_hash, calendars = await self._get_data()
        for calendar in calendars:
            if calendar["id"] == calendar_id:
                return commit_hash, calendar
        return commit_hash, None

    async def search_calendar_events(
        self,
        calendar_id: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        keyword: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[list[dict]]]:
        """Filter by overlapping local dates and keyword, then sort by start."""
        commit_hash, calendar = await self.get_calendar(calendar_id)
        if calendar is None:
            return commit_hash, None
        events = filter_calendar_events(calendar["events"], start, end, keyword)
        return commit_hash, sorted(events, key=lambda event: (event["start"], event["id"]))

    async def get_calendar_event(
        self, calendar_id: str, event_id: str
    ) -> tuple[Optional[str], Optional[dict]]:
        """Get a single event within its calendar."""
        commit_hash, calendar = await self.get_calendar(calendar_id)
        if calendar is not None:
            for event in calendar["events"]:
                if event["id"] == event_id:
                    return commit_hash, event
        return commit_hash, None


calendars_service = CalendarsService()
