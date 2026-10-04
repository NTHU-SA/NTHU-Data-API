"""Campus calendar queries backed by the shared dataset snapshot."""

import hashlib
import json
from datetime import date
from typing import Optional

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.utils.calendars import filter_calendar_events

JSON_PATH = "calendars.json"
LIBRARY_JSON_PATH = "libraries/calendars.json"
LIBRARY_PREFIX = "library-"


class CalendarsService:
    async def get_all_calendars(self) -> tuple[Optional[str], list[dict]]:
        """Get calendar metadata without events."""
        campus_version, campus = await self._get_data(JSON_PATH)
        library_version, libraries = await self._get_data(LIBRARY_JSON_PATH)
        # A list spans two snapshots; neither source's version alone identifies it.
        commit_hash = None
        if campus_version is not None and library_version is not None:
            commit_hash = hashlib.sha256(
                json.dumps([campus_version, library_version]).encode()
            ).hexdigest()
        calendars = campus + [self._library_calendar(calendar) for calendar in libraries]
        return commit_hash, [
            {key: value for key, value in calendar.items() if key != "events"}
            for calendar in calendars
        ]

    async def _get_data(self, path: str) -> tuple[Optional[str], list[dict]]:
        result = await nthudata.get(path)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")
        return result

    @staticmethod
    def _library_calendar(calendar: dict) -> dict:
        return {
            **calendar,
            "id": f"{LIBRARY_PREFIX}{calendar['id']}",
            "category": "library",
            "source": "NTHU Library",
        }

    async def get_calendar(self, calendar_id: str) -> tuple[Optional[str], Optional[dict]]:
        """Get one calendar, including its events."""
        is_library = calendar_id.startswith(LIBRARY_PREFIX)
        path = LIBRARY_JSON_PATH if is_library else JSON_PATH
        source_id = calendar_id.removeprefix(LIBRARY_PREFIX) if is_library else calendar_id
        commit_hash, calendars = await self._get_data(path)
        for calendar in calendars:
            if calendar["id"] == source_id:
                return commit_hash, self._library_calendar(calendar) if is_library else calendar
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
