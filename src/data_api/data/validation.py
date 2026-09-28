"""Validate published payloads before any reader can observe them."""

import json
from collections.abc import Sequence
from datetime import date, datetime
from functools import lru_cache

from pydantic import BaseModel, TypeAdapter

from data_api.api.schemas.announcements import AnnouncementDetail
from data_api.api.schemas.calendars import Calendar, CalendarEvent
from data_api.api.schemas.departments import Department
from data_api.api.schemas.dining import DiningBuilding
from data_api.api.schemas.libraries import LibraryCalendar, LibraryCalendarEvent, LibraryRssItem
from data_api.api.schemas.newsletters import NewsletterInfo
from data_api.data.nthudata import FetchFailure, JsonData


class AnnouncementSource(BaseModel):
    title: str
    link: str
    language: str
    department: str


class Coordinates(BaseModel):
    latitude: str
    longitude: str


class CalendarPayload(LibraryCalendar):
    events: list[LibraryCalendarEvent]


class CampusCalendarPayload(Calendar):
    events: list[CalendarEvent]


class LibraryPayload(BaseModel):
    name: str


@lru_cache
def _adapters() -> dict[str, TypeAdapter]:
    return {
        "/announcements.json": TypeAdapter(list[AnnouncementDetail]),
        "/announcements_list.json": TypeAdapter(list[AnnouncementSource]),
        "/dining.json": TypeAdapter(list[DiningBuilding]),
        "/directory.json": TypeAdapter(list[Department]),
        "/newsletters.json": TypeAdapter(list[NewsletterInfo]),
        "/maps.json": TypeAdapter(dict[str, dict[str, Coordinates]]),
        "/libraries.json": TypeAdapter(list[LibraryPayload]),
        "/libraries/rss.json": TypeAdapter(dict[str, list[LibraryRssItem]]),
        "/libraries/calendars.json": TypeAdapter(list[CalendarPayload]),
        "/calendars.json": TypeAdapter(list[CampusCalendarPayload]),
    }


def _validate_calendar_events(
    calendars: Sequence[CalendarPayload | CampusCalendarPayload],
) -> None:
    for calendar in calendars:
        for event in calendar.events:
            try:
                parse = date.fromisoformat if event.all_day else datetime.fromisoformat
                if parse(event.end) < parse(event.start):
                    raise ValueError("End precedes start")
            except (ValueError, TypeError) as exc:
                raise FetchFailure("validation") from exc


def validate_dataset(endpoint: str, raw: JsonData) -> JsonData:
    adapter = _adapters().get(endpoint)
    if adapter is not None:
        expected_type = dict if endpoint in {"/maps.json", "/libraries/rss.json"} else list
        if not isinstance(raw, expected_type):
            raise FetchFailure("payload_type")
        # JSON strict mode accepts enum/URL strings without coercing booleans or numbers.
        parsed = adapter.validate_json(json.dumps(raw), strict=True)
        if endpoint in {"/libraries/calendars.json", "/calendars.json"}:
            _validate_calendar_events(parsed)
    # Preserve upstream fields and representation; response serialization stays unchanged.
    return raw
