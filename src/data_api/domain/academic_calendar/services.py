"""Read and parse the public NTHU academic-calendar ICS feed."""

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256

import httpx
from icalendar import Calendar

OFFICIAL_NTHU_SOURCE_ID = "official_nthu"
OFFICIAL_NTHU_ICS_URL = (
    "https://calendar.google.com/calendar/ical/" "nthu.acad%40gmail.com/public/basic.ics"
)
MAX_OFFICIAL_NTHU_ICS_BYTES = 5 * 1024 * 1024


class AcademicCalendarParseError(ValueError):
    """Raised when the public source does not contain a valid iCalendar document."""


class AcademicCalendarSourceError(RuntimeError):
    """Raised when the public calendar source cannot be retrieved as text."""


@dataclass(frozen=True)
class AcademicCalendarEvent:
    """A source-faithful event parsed from the NTHU public ICS feed."""

    uid: str
    summary: str
    start: date | datetime
    end: date | datetime | None
    all_day: bool
    end_is_exclusive: bool
    status: str | None


@dataclass(frozen=True)
class ParsedAcademicCalendar:
    """Parsed calendar content plus the source metadata needed for later API provenance."""

    source_id: str
    source_url: str
    calendar_name: str | None
    calendar_timezone: str | None
    raw_snapshot_sha256: str
    events: list[AcademicCalendarEvent]
    skipped_event_count: int


async def fetch_official_nthu_ics(client: httpx.AsyncClient | None = None) -> str:
    """Fetch the public official NTHU academic calendar as UTF-8 ICS text."""
    owns_client = client is None
    active_client = client or httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=False,
        headers={"Accept": "text/calendar, application/octet-stream;q=0.9"},
    )

    try:
        async with active_client.stream(
            "GET", OFFICIAL_NTHU_ICS_URL, follow_redirects=False
        ) as response:
            response.raise_for_status()
            _raise_if_oversized(response.headers.get("Content-Length"))

            content = bytearray()
            async for chunk in response.aiter_bytes():
                if len(content) + len(chunk) > MAX_OFFICIAL_NTHU_ICS_BYTES:
                    raise AcademicCalendarSourceError(
                        "Official NTHU academic calendar exceeds the parser size limit."
                    )
                content.extend(chunk)

        return bytes(content).decode("utf-8")
    except (httpx.HTTPError, UnicodeDecodeError) as exc:
        raise AcademicCalendarSourceError(
            f"Failed to fetch official NTHU academic calendar: {exc}"
        ) from exc
    finally:
        if owns_client:
            await active_client.aclose()


def parse_official_nthu_ics(ics_content: str) -> ParsedAcademicCalendar:
    """Parse public ICS text without rewriting all-day or timed-event semantics."""
    if "BEGIN:VCALENDAR" not in ics_content:
        raise AcademicCalendarParseError("Expected a VCALENDAR document.")

    try:
        calendar = Calendar.from_ical(ics_content)
    except (TypeError, ValueError) as exc:
        raise AcademicCalendarParseError(f"Unable to parse VCALENDAR document: {exc}") from exc

    events = []
    skipped_event_count = 0
    for component in calendar.walk("VEVENT"):
        try:
            events.append(_parse_event(component))
        except AcademicCalendarParseError:
            skipped_event_count += 1
    calendar_name = _text_value(calendar.get("X-WR-CALNAME"))
    calendar_timezone = _text_value(calendar.get("X-WR-TIMEZONE"))

    return ParsedAcademicCalendar(
        source_id=OFFICIAL_NTHU_SOURCE_ID,
        source_url=OFFICIAL_NTHU_ICS_URL,
        calendar_name=calendar_name,
        calendar_timezone=calendar_timezone,
        raw_snapshot_sha256=sha256(ics_content.encode("utf-8")).hexdigest(),
        events=events,
        skipped_event_count=skipped_event_count,
    )


def _parse_event(component) -> AcademicCalendarEvent:
    uid = _required_text_value(component, "UID")
    summary = _required_text_value(component, "SUMMARY")
    start = _required_decoded_value(component, "DTSTART")
    end = _optional_decoded_value(component, "DTEND")
    all_day = isinstance(start, date) and not isinstance(start, datetime)

    return AcademicCalendarEvent(
        uid=uid,
        summary=summary,
        start=start,
        end=end,
        all_day=all_day,
        end_is_exclusive=end is not None,
        status=_text_value(component.get("STATUS")),
    )


def _required_text_value(component, property_name: str) -> str:
    value = _text_value(component.get(property_name))
    if not value:
        raise AcademicCalendarParseError(f"VEVENT is missing required {property_name}.")
    return value


def _required_decoded_value(component, property_name: str) -> date | datetime:
    value = _optional_decoded_value(component, property_name)
    if value is None:
        raise AcademicCalendarParseError(f"VEVENT is missing required {property_name}.")
    return value


def _optional_decoded_value(component, property_name: str) -> date | datetime | None:
    if component.get(property_name) is None:
        return None
    try:
        value = component.decoded(property_name)
    except (KeyError, ValueError) as exc:
        raise AcademicCalendarParseError(f"VEVENT has invalid {property_name}: {exc}") from exc

    if not isinstance(value, (date, datetime)):
        raise AcademicCalendarParseError(f"VEVENT has unsupported {property_name} value.")
    return value


def _text_value(value) -> str | None:
    return str(value) if value is not None else None


def _raise_if_oversized(content_length: str | None) -> None:
    if content_length is None:
        return

    try:
        declared_size = int(content_length)
    except ValueError:
        return

    if declared_size > MAX_OFFICIAL_NTHU_ICS_BYTES:
        raise AcademicCalendarSourceError(
            "Official NTHU academic calendar exceeds the parser size limit."
        )
