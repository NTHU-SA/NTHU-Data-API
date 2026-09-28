"""Campus calendar queries and published snapshot lifecycle."""

from copy import deepcopy

import httpx
import pytest
from test_data_manager import Clock, Publisher

from data_api.api.api import app
from data_api.data.manager import nthudata
from data_api.data.nthudata import Freshness


def make_event(event_id, title, start, end, all_day=True, description=None):
    return {
        "id": event_id,
        "title": title,
        "description": description,
        "start": start,
        "end": end,
        "all_day": all_day,
    }


EVENTS = [
    make_event("last", "Semester ends", "2026-10-31", "2026-11-01"),
    make_event(
        "overnight", "Workshop", "2026-10-03T22:00:00+08:00", "2026-10-04T00:00:00+08:00", False
    ),
    make_event("b", "Registration", "2026-10-01", "2026-10-02", description="Select C++ [AI]"),
    make_event("spanning", "Selection period", "2026-09-28", "2026-10-03"),
    make_event("before", "Holiday", "2026-09-30", "2026-10-01"),
    make_event("a", "Classes begin", "2026-10-01", "2026-10-02"),
    make_event(
        "crossing", "Night event", "2026-10-05T22:00:00+08:00", "2026-10-06T01:00:00+08:00", False
    ),
]
CALENDARS = [
    {
        "id": "academic",
        "name": "Academic calendar",
        "description": None,
        "timezone": "Asia/Taipei",
        "events": EVENTS,
    },
    {
        "id": "future-calendar",
        "name": "Additional calendar",
        "description": None,
        "timezone": "Asia/Taipei",
        "events": [],
    },
]
PATHS = [
    "/calendars/",
    "/calendars/academic",
    "/calendars/academic/events",
    "/calendars/academic/events/a",
]
EVENTS_PATH = "/calendars/academic/events"


@pytest.fixture
async def runtime(monkeypatch):
    clock, publisher = Clock(), Publisher(deepcopy(CALENDARS), "calendars.json")
    monkeypatch.setattr(nthudata, "clock", clock)
    async with nthudata.lifespan(publisher.client()):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, publisher, clock


async def test_calendar_metadata_and_dynamic_ids(runtime):
    client, publisher, _ = runtime
    response = await client.get("/calendars/")
    assert response.status_code == 200
    assert response.json() == [
        {key: value for key, value in calendar.items() if key != "events"} for calendar in CALENDARS
    ]
    assert response.headers["X-Data-Commit-Hash"] == "a"
    for metadata in response.json():
        detail = await client.get(f"/calendars/{metadata['id']}")
        assert detail.status_code == 200
        assert detail.json() == metadata
        assert detail.headers["X-Data-Commit-Hash"] == "a"
    assert publisher.calls.count("/calendars.json") == 1


@pytest.mark.parametrize(
    "params,expected",
    [
        ({}, ["spanning", "before", "a", "b", "overnight", "crossing", "last"]),
        ({"start": "2026-10-01", "end": "2026-10-01"}, ["spanning", "a", "b"]),
        ({"start": "2026-10-02", "end": "2026-10-02"}, ["spanning"]),
        ({"start": "2026-10-03", "end": "2026-10-03"}, ["overnight"]),
        ({"start": "2026-10-04", "end": "2026-10-04"}, []),
        ({"start": "2026-10-06", "end": "2026-10-06"}, ["crossing"]),
        ({"start": "2026-10-07"}, ["last"]),
        ({"end": "2026-09-30"}, ["spanning", "before"]),
        ({"keyword": "  REGISTRATION  "}, ["b"]),
        ({"keyword": "c++ [ai]"}, ["b"]),
        ({"keyword": ".*"}, []),
        ({"keyword": "select"}, ["spanning", "b"]),
        ({"start": "2026-10-02", "end": "2026-10-02", "keyword": "select"}, ["spanning"]),
        ({"start": "2026-10-07", "keyword": "select"}, []),
    ],
)
async def test_event_filters(runtime, params, expected):
    client, publisher, _ = runtime
    response = await client.get(EVENTS_PATH, params=params)
    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == expected
    assert response.headers["X-Total-Count"] == str(len(expected))
    assert response.headers["X-Data-Commit-Hash"] == "a"
    assert publisher.payload == CALENDARS


async def test_pagination_after_filtering_and_sorting(runtime):
    client, _, _ = runtime
    response = await client.get(
        EVENTS_PATH,
        params={"start": "2026-10-01", "end": "2026-10-03", "limit": 2, "offset": 1},
    )
    assert response.status_code == 200
    assert [event["id"] for event in response.json()] == ["a", "b"]
    assert response.headers["X-Total-Count"] == "4"
    response = await client.get(EVENTS_PATH, params={"offset": 1000})
    assert response.json() == []
    assert response.headers["X-Total-Count"] == "7"


async def test_default_limit_and_blank_keyword(runtime):
    client, publisher, _ = runtime
    publisher.payload[0]["events"] = [
        make_event(f"{index:03}", "Event", "2026-10-01", "2026-10-02") for index in range(101)
    ]
    response = await client.get(EVENTS_PATH, params={"keyword": "  "})
    assert len(response.json()) == 100
    assert response.headers["X-Total-Count"] == "101"
    response = await client.get(EVENTS_PATH, params={"limit": 1000})
    assert len(response.json()) == 101


@pytest.mark.parametrize(
    "params,status",
    [
        ({"start": "2026-11-01", "end": "2026-10-01"}, 400),
        ({"start": "soon"}, 422),
        ({"end": "2026-02-30"}, 422),
        ({"limit": 0}, 422),
        ({"limit": 1001}, 422),
        ({"offset": -1}, 422),
    ],
)
async def test_invalid_queries_do_not_fetch(runtime, params, status):
    client, publisher, _ = runtime
    response = await client.get(EVENTS_PATH, params=params)
    assert response.status_code == status
    assert publisher.calls == []


async def test_single_event_preserves_source_shape(runtime):
    client, _, _ = runtime
    response = await client.get(f"{EVENTS_PATH}/b")
    assert response.status_code == 200
    assert response.json() == EVENTS[2]
    assert response.headers["X-Data-Commit-Hash"] == "a"


@pytest.mark.parametrize(
    "path",
    [
        "/calendars/missing",
        "/calendars/missing/events",
        "/calendars/missing/events/a",
        "/calendars/future-calendar/events/a",
        f"{EVENTS_PATH}/missing",
    ],
)
async def test_missing_calendar_or_event(runtime, path):
    client, _, _ = runtime
    assert (await client.get(path)).status_code == 404


async def test_empty_calendar_and_empty_dataset(runtime):
    client, publisher, clock = runtime
    response = await client.get("/calendars/future-calendar/events")
    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["X-Total-Count"] == "0"
    publisher.payload, publisher.version = [], "empty"
    clock.advance()
    response = await client.get("/calendars/")
    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["X-Data-Commit-Hash"] == "empty"
    assert (await client.get(EVENTS_PATH)).status_code == 404


@pytest.mark.parametrize("path", PATHS)
async def test_unavailable_dataset(runtime, path):
    client, publisher, _ = runtime
    publisher.data_error = 503
    response = await client.get(path)
    assert response.status_code == 503
    assert response.json() == {"detail": "Service temporarily unavailable"}


@pytest.mark.parametrize("path", PATHS)
async def test_unknown_version_header_is_omitted(runtime, path):
    client, publisher, _ = runtime
    publisher.version = None
    response = await client.get(path)
    assert response.status_code == 200
    assert "X-Data-Commit-Hash" not in response.headers


@pytest.mark.parametrize(
    "invalid",
    [
        {},
        [{"id": "academic"}],
        [{**CALENDARS[0], "events": None}],
        [{**CALENDARS[0], "events": [{**EVENTS[0], "start": "invalid"}]}],
        [{**CALENDARS[0], "events": [{**EVENTS[0], "end": "2026-09-01"}]}],
        [{**CALENDARS[0], "events": [{**EVENTS[0], "all_day": "true"}]}],
    ],
)
@pytest.mark.parametrize("initial_loaded", [True, False])
async def test_invalid_payload_preserves_snapshot_and_fails_cold_start(
    runtime, invalid, initial_loaded
):
    client, publisher, clock = runtime
    if initial_loaded:
        original = (await client.get(EVENTS_PATH)).json()
    publisher.payload, publisher.version = invalid, "invalid"
    clock.advance()
    response = await client.get(EVENTS_PATH)
    if initial_loaded:
        assert response.status_code == 200
        assert response.json() == original
        assert response.headers["X-Data-Commit-Hash"] == "a"
        assert nthudata.states["/calendars.json"].freshness == Freshness.STALE
    else:
        assert response.status_code == 503
        assert nthudata.states["/calendars.json"].freshness == Freshness.UNAVAILABLE


async def test_runtime_refresh_and_upstream_failure(runtime):
    client, publisher, clock = runtime
    assert (await client.get(f"{EVENTS_PATH}/b")).json()["title"] == "Registration"
    publisher.version = "b"
    publisher.payload[0]["events"][2]["title"] = "Updated registration"
    clock.advance()
    response = await client.get(f"{EVENTS_PATH}/b")
    assert response.json()["title"] == "Updated registration"
    assert response.headers["X-Data-Commit-Hash"] == "b"
    publisher.data_error = 503
    clock.advance()
    response = await client.get(f"{EVENTS_PATH}/b")
    assert response.status_code == 200
    assert response.json()["title"] == "Updated registration"
    assert response.headers["X-Data-Commit-Hash"] == "b"


def test_openapi_calendar_contract():
    schema = app.openapi()
    assert schema["paths"]["/calendars/"]["get"]["operationId"] == "getAllCalendars"
    search = schema["paths"][EVENTS_PATH.replace("academic", "{calendar_id}")]["get"]
    assert search["operationId"] == "searchCalendarEvents"
    assert {parameter["name"] for parameter in search["parameters"]} == {
        "calendar_id",
        "start",
        "end",
        "keyword",
        "limit",
        "offset",
    }
