"""Tests for the official NTHU academic-calendar source adapter."""

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest

from data_api.domain.academic_calendar.services import (
    MAX_OFFICIAL_NTHU_ICS_BYTES,
    OFFICIAL_NTHU_ICS_URL,
    OFFICIAL_NTHU_SOURCE_ID,
    AcademicCalendarParseError,
    AcademicCalendarSourceError,
    fetch_official_nthu_ics,
    parse_official_nthu_ics,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "academic_calendar"
ICS_FIXTURE = FIXTURE_DIR / "official_nthu_115_excerpt.ics"
METADATA_FIXTURE = FIXTURE_DIR / "official_nthu_115_excerpt.source.json"


def load_fixture() -> str:
    """Load the public NTHU ICS excerpt used by parser tests."""
    return ICS_FIXTURE.read_text(encoding="utf-8")


class TestOfficialNTHUCalendarParser:
    """The adapter preserves source semantics instead of guessing dates."""

    def test_uses_the_stable_public_google_ics_feed(self):
        assert OFFICIAL_NTHU_ICS_URL == (
            "https://calendar.google.com/calendar/ical/" "nthu.acad%40gmail.com/public/basic.ics"
        )

    def test_parses_calendar_timezone_and_source_metadata(self):
        parsed = parse_official_nthu_ics(load_fixture())
        metadata = json.loads(METADATA_FIXTURE.read_text(encoding="utf-8"))

        assert parsed.source_id == OFFICIAL_NTHU_SOURCE_ID
        assert parsed.source_url == OFFICIAL_NTHU_ICS_URL
        assert parsed.calendar_name == "國立清華大學行事曆"
        assert parsed.calendar_timezone == "Asia/Taipei"
        assert (
            parsed.raw_snapshot_sha256 == hashlib.sha256(load_fixture().encode("utf-8")).hexdigest()
        )
        assert metadata["source_id"] == parsed.source_id
        assert metadata["source_url"] == parsed.source_url

    def test_preserves_all_day_start_and_exclusive_end(self):
        parsed = parse_official_nthu_ics(load_fixture())
        event = next(event for event in parsed.events if event.uid.startswith("475cegj"))

        assert event.all_day is True
        assert event.start == date(2026, 8, 18)
        assert event.end == date(2026, 8, 19)
        assert event.end_is_exclusive is True
        assert "Fall 2026 (8/18-8/20)" in event.summary

    def test_preserves_utc_timed_events_without_coercing_to_calendar_timezone(self):
        parsed = parse_official_nthu_ics(load_fixture())
        event = next(event for event in parsed.events if event.uid.startswith("oqovglv"))

        assert event.all_day is False
        assert event.start == datetime(2011, 4, 23, 7, 30, tzinfo=timezone.utc)
        assert event.end == datetime(2011, 4, 23, 11, 0, tzinfo=timezone.utc)
        assert parsed.calendar_timezone == "Asia/Taipei"

    def test_rejects_malformed_icalendar_content(self):
        with pytest.raises(AcademicCalendarParseError, match="VCALENDAR"):
            parse_official_nthu_ics("BEGIN:VEVENT\nSUMMARY:not a calendar\nEND:VEVENT")

    def test_skips_malformed_event_without_discarding_valid_events(self):
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
X-WR-TIMEZONE:Asia/Taipei
BEGIN:VEVENT
UID:valid@example.test
DTSTART;VALUE=DATE:20260907
DTEND;VALUE=DATE:20260908
SUMMARY:Valid event
END:VEVENT
BEGIN:VEVENT
UID:missing-summary@example.test
DTSTART;VALUE=DATE:20260908
DTEND;VALUE=DATE:20260909
END:VEVENT
END:VCALENDAR
"""

        parsed = parse_official_nthu_ics(ics_content)

        assert [event.uid for event in parsed.events] == ["valid@example.test"]
        assert parsed.skipped_event_count == 1


class TestOfficialNTHUCalendarSource:
    """Network failures have an explicit source error rather than silent empty data."""

    async def test_raises_source_error_when_public_ics_is_unavailable(self):
        def unavailable(_: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="maintenance")

        async with httpx.AsyncClient(transport=httpx.MockTransport(unavailable)) as client:
            with pytest.raises(AcademicCalendarSourceError, match="503"):
                await fetch_official_nthu_ics(client=client)

    async def test_rejects_ics_that_exceeds_the_parser_size_limit(self):
        def oversized(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"Content-Length": str(MAX_OFFICIAL_NTHU_ICS_BYTES + 1)},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(oversized)) as client:
            with pytest.raises(AcademicCalendarSourceError, match="size limit"):
                await fetch_official_nthu_ics(client=client)
