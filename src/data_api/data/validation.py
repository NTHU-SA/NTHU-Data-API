"""Validate published payloads before any reader can observe them."""

import json
from collections.abc import Sequence
from datetime import date, datetime
from functools import lru_cache

from pydantic import BaseModel, HttpUrl, TypeAdapter

from data_api.data.nthudata import FetchFailure, JsonData
from data_api.models.announcements import AnnouncementDetail, AnnouncementSource
from data_api.models.calendars import Calendar, CalendarEvent
from data_api.models.departments import Department
from data_api.models.dining import DiningBuilding
from data_api.models.libraries import LibraryRssItem
from data_api.models.newsletters import NewsletterInfo


class Coordinates(BaseModel):
    latitude: str
    longitude: str


class CalendarPayload(Calendar):
    events: list[CalendarEvent]


class LibraryCalendarPayload(CalendarPayload):
    url: HttpUrl


class LibraryPayload(BaseModel):
    name: str


LIBRARIES_RSS_ENDPOINT = "/libraries/rss.json"
LIBRARIES_CALENDARS_ENDPOINT = "/libraries/calendars.json"
CALENDARS_ENDPOINT = "/calendars.json"


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
        LIBRARIES_RSS_ENDPOINT: TypeAdapter(dict[str, list[LibraryRssItem]]),
        LIBRARIES_CALENDARS_ENDPOINT: TypeAdapter(list[LibraryCalendarPayload]),
        CALENDARS_ENDPOINT: TypeAdapter(list[CalendarPayload]),
    }


def _validate_calendar_events(
    calendars: Sequence[CalendarPayload],
) -> None:
    for calendar in calendars:
        for event in calendar.events:
            try:
                parse = date.fromisoformat if event.all_day else datetime.fromisoformat
                if parse(event.end) < parse(event.start):
                    raise ValueError("End precedes start")
            except (ValueError, TypeError) as exc:
                raise FetchFailure("validation") from exc


def _normalize_library_rss(
    raw: dict[str, list[dict]], parsed: dict[str, list[LibraryRssItem]]
) -> dict[str, list[dict]]:
    normalized = {}
    for feed, items in raw.items():
        normalized[feed] = []
        for item, model in zip(items, parsed[feed], strict=True):
            result = dict(item)
            if model.image is not None:
                result["image"] = {
                    **item["image"],
                    "url": str(model.image.url) if model.image.url is not None else None,
                    "link": str(model.image.link) if model.image.link is not None else None,
                }
            normalized[feed].append(result)
    return normalized


def _validate_calendars(endpoint: str, parsed: Sequence[CalendarPayload]) -> None:
    ids = [calendar.id for calendar in parsed]
    has_reserved_prefix = endpoint == CALENDARS_ENDPOINT and any(
        calendar_id.startswith("library-") for calendar_id in ids
    )
    if len(ids) != len(set(ids)) or has_reserved_prefix:
        raise FetchFailure("validation")
    _validate_calendar_events(parsed)


def validate_dataset(endpoint: str, raw: JsonData) -> JsonData:
    adapter = _adapters().get(endpoint)
    if adapter is None:
        # Other datasets preserve their upstream fields and representation.
        return raw
    expected_type = dict if endpoint in {"/maps.json", LIBRARIES_RSS_ENDPOINT} else list
    if not isinstance(raw, expected_type):
        raise FetchFailure("payload_type")
    # JSON strict mode accepts enum/URL strings without coercing booleans or numbers.
    parsed = adapter.validate_json(json.dumps(raw), strict=True)
    if endpoint == LIBRARIES_RSS_ENDPOINT:
        return _normalize_library_rss(raw, parsed)
    if endpoint in {LIBRARIES_CALENDARS_ENDPOINT, CALENDARS_ENDPOINT}:
        _validate_calendars(endpoint, parsed)
    return raw
