"""
Libraries domain service.

Handles library data fetching and search, plus the library RSS feeds and
opening-hours calendars crawled by NTHU-Data-Scraper.
"""

from datetime import date
from typing import Optional

from thefuzz import fuzz

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.utils.calendars import filter_calendar_events, get_event_date_range

JSON_PATH = "libraries.json"
RSS_JSON_PATH = "libraries/rss.json"
CALENDARS_JSON_PATH = "libraries/calendars.json"
FUZZY_SEARCH_THRESHOLD = 70


class LibrariesService:
    """Service for library data operations."""

    async def get_all_libraries(self) -> tuple[Optional[str], list[dict]]:
        """Get all libraries."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")
        return result

    async def get_library_by_name(self, name: str) -> tuple[Optional[str], Optional[dict]]:
        """Get library by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")

        commit_hash, libraries_data = result
        for library in libraries_data:
            if library["name"] == name:
                return commit_hash, library
        return commit_hash, None

    async def fuzzy_search_libraries(self, query: str) -> tuple[Optional[str], list[dict]]:
        """Fuzzy search libraries by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")

        commit_hash, libraries_data = result
        results_with_score = []
        for library in libraries_data:
            similarity = fuzz.partial_ratio(query, library["name"])
            if similarity >= FUZZY_SEARCH_THRESHOLD:
                results_with_score.append((similarity, library))

        results_with_score.sort(key=lambda x: x[0], reverse=True)
        return commit_hash, [lib for _, lib in results_with_score]

    async def get_rss_items(self, rss_type: str) -> tuple[Optional[str], Optional[list[dict]]]:
        """Get the items of one library RSS feed."""
        result = await nthudata.get(RSS_JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")

        commit_hash, rss_data = result
        return commit_hash, rss_data.get(rss_type)

    async def get_all_calendars(self) -> tuple[Optional[str], list[dict]]:
        """Get calendar metadata without events."""
        result = await nthudata.get(CALENDARS_JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")

        commit_hash, calendars = result
        return commit_hash, [
            {key: value for key, value in calendar.items() if key != "events"}
            for calendar in calendars
        ]

    async def get_calendar(self, calendar_id: str) -> tuple[Optional[str], Optional[dict]]:
        """Get one calendar, including its events."""
        result = await nthudata.get(CALENDARS_JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")

        commit_hash, calendars = result
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
        """Get the events of a calendar filtered by date range and keyword."""
        commit_hash, calendar = await self.get_calendar(calendar_id)
        if calendar is None:
            return commit_hash, None
        return commit_hash, filter_calendar_events(calendar["events"], start, end, keyword)

    async def get_calendar_event(
        self, calendar_id: str, event_id: str
    ) -> tuple[Optional[str], Optional[dict]]:
        """Get a single event by id."""
        commit_hash, calendar = await self.get_calendar(calendar_id)
        if calendar is None:
            return commit_hash, None
        for event in calendar["events"]:
            if event["id"] == event_id:
                return commit_hash, event
        return commit_hash, None


# Global service instance
libraries_service = LibrariesService()
