"""Campus calendar queries and published snapshot lifecycle."""

import hashlib
import json
from copy import deepcopy

import httpx
import pytest
from test_data_manager import Clock, Publisher

from data_api.api.api import app
from data_api.api.schemas.calendars import Calendar
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
def library_publisher():
    return Publisher([], "libraries/calendars.json")


@pytest.fixture
async def runtime(monkeypatch, library_publisher):
    clock, publisher = Clock(), Publisher(deepcopy(CALENDARS), "calendars.json")
    monkeypatch.setattr(nthudata, "clock", clock)

    async def handler(request):
        if request.url.path == "/libraries/calendars.json":
            return await library_publisher(request)
        response = await publisher(request)
        if request.url.path == "/file_details.json" and response.status_code == 200:
            manifest = response.json()
            manifest["file_details"]["/"].extend(library_publisher.manifest()["file_details"]["/"])
            return httpx.Response(200, json=manifest)
        return response

    async with nthudata.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, publisher, clock


async def test_calendar_metadata_and_dynamic_ids(runtime):
    client, publisher, _ = runtime
    response = await client.get("/calendars/")
    assert response.status_code == 200
    assert response.json() == [
        Calendar.model_validate(calendar).model_dump(mode="json") for calendar in CALENDARS
    ]
    assert (
        response.headers["X-Data-Commit-Hash"]
        == hashlib.sha256(json.dumps(["a", "a"]).encode()).hexdigest()
    )
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
    assert (
        response.headers["X-Data-Commit-Hash"]
        == hashlib.sha256(json.dumps(["empty", "a"]).encode()).hexdigest()
    )
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
        [{**CALENDARS[0], "id": "library-main"}],
        [CALENDARS[0], CALENDARS[0]],
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
    assert not any(path.startswith("/libraries/calendars") for path in schema["paths"])
    assert not any(name.startswith("LibraryCalendar") for name in schema["components"]["schemas"])
    assert schema["paths"]["/calendars"]["get"]["operationId"] == "getAllCalendars"
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
    for path, operations in schema["paths"].items():
        if "{calendar_id}" not in path:
            continue
        parameter = next(
            parameter
            for parameter in operations["get"]["parameters"]
            if parameter["name"] == "calendar_id"
        )
        assert "/calendars " in parameter["description"]
        assert "/calendars/" not in parameter["description"]


async def test_unified_list_and_all_library_branches(runtime, library_publisher):
    client, publisher, _ = runtime
    library_publisher.version = "library-version"
    library_publisher.payload = [
        {
            "id": branch,
            "name": f"{branch} opening hours",
            "url": f"https://calendar.google.com/calendar/embed?src={branch}",
            "events": deepcopy(EVENTS),
        }
        for branch in ["main", "hss", "nanda"]
    ]
    original = deepcopy(library_publisher.payload)
    response = await client.get("/calendars/")
    assert response.status_code == 200
    assert [calendar["id"] for calendar in response.json()] == [
        "academic",
        "future-calendar",
        "library-main",
        "library-hss",
        "library-nanda",
    ]
    for metadata in response.json()[2:]:
        assert metadata["category"] == "library"
        assert metadata["source"] == "NTHU Library"
        assert metadata["description"] is None
        assert "events" not in metadata
        path = f"/calendars/{metadata['id']}"
        detail = await client.get(path)
        assert detail.json() == metadata
        assert detail.headers["X-Data-Commit-Hash"] == "library-version"
        events = await client.get(
            f"{path}/events",
            params={"start": "2026-10-01", "end": "2026-10-03", "limit": 2, "offset": 1},
        )
        assert events.status_code == 200
        assert events.headers["X-Total-Count"] == "4"
        assert events.headers["X-Data-Commit-Hash"] == "library-version"
        assert [event["id"] for event in events.json()] == ["a", "b"]
        keyword = await client.get(f"{path}/events", params={"keyword": "c++ [ai]"})
        assert [event["id"] for event in keyword.json()] == ["b"]
        event = await client.get(f"{path}/events/b")
        assert event.json() == EVENTS[2]
        assert event.headers["X-Data-Commit-Hash"] == "library-version"
        assert (await client.get(f"{path}/events/missing")).status_code == 404
    assert publisher.payload == CALENDARS
    assert library_publisher.payload == original
    assert library_publisher.calls.count("/libraries/calendars.json") == 1


@pytest.mark.parametrize("unavailable", ["campus", "library"])
async def test_individual_calendars_do_not_depend_on_other_dataset(
    runtime, library_publisher, unavailable
):
    client, publisher, _ = runtime
    library_publisher.payload = [
        {"id": "main", "url": "https://example.com/calendar", "events": deepcopy(EVENTS)}
    ]
    if unavailable == "campus":
        publisher.data_error = 503
        path = "/calendars/library-main"
    else:
        library_publisher.data_error = 503
        path = "/calendars/academic"
    for suffix in ["", "/events", "/events/b"]:
        assert (await client.get(f"{path}{suffix}")).status_code == 200
    assert (await client.get("/calendars/")).status_code == 503


async def test_library_refresh_versions_and_stale_snapshot(runtime, library_publisher):
    client, publisher, clock = runtime
    library_publisher.payload = [
        {"id": "main", "url": "https://example.com/calendar", "events": deepcopy(EVENTS)}
    ]
    first = await client.get("/calendars/")
    library_publisher.version = "b"
    library_publisher.payload[0]["events"][2]["title"] = "Updated library event"
    clock.advance()
    second = await client.get("/calendars/")
    assert first.headers["X-Data-Commit-Hash"] != second.headers["X-Data-Commit-Hash"]
    event = await client.get("/calendars/library-main/events/b")
    assert event.json()["title"] == "Updated library event"
    assert event.headers["X-Data-Commit-Hash"] == "b"
    assert publisher.version == "a"
    publisher.version = "campus-b"
    clock.advance()
    third = await client.get("/calendars/")
    assert second.headers["X-Data-Commit-Hash"] != third.headers["X-Data-Commit-Hash"]
    library_publisher.version = "c"
    library_publisher.data_error = 503
    clock.advance()
    event = await client.get("/calendars/library-main/events/b")
    assert event.status_code == 200
    assert event.json()["title"] == "Updated library event"
    assert event.headers["X-Data-Commit-Hash"] == "b"
    assert nthudata.states["/libraries/calendars.json"].freshness == Freshness.STALE


@pytest.mark.parametrize(
    "invalid",
    [
        {"id": "main", "events": []},
        {"id": "main", "url": "invalid", "events": []},
        {"id": "main", "url": "https://example.com", "events": None},
        {
            "id": "main",
            "url": "https://example.com",
            "events": [{**EVENTS[0], "all_day": "true"}],
        },
        {
            "id": "main",
            "url": "https://example.com",
            "events": [{**EVENTS[0], "end": "2026-01-01"}],
        },
    ],
)
@pytest.mark.parametrize("initial_loaded", [False, True])
async def test_invalid_library_payload_preserves_snapshot(
    runtime, library_publisher, invalid, initial_loaded
):
    client, _, clock = runtime
    library_publisher.payload = [
        {"id": "main", "url": "https://example.com", "events": deepcopy(EVENTS)}
    ]
    path = "/calendars/library-main/events"
    if initial_loaded:
        original = (await client.get(path)).json()
    library_publisher.payload, library_publisher.version = [invalid], "invalid"
    clock.advance()
    response = await client.get(path)
    if initial_loaded:
        assert response.status_code == 200
        assert response.json() == original
        assert response.headers["X-Data-Commit-Hash"] == "a"
        assert nthudata.states["/libraries/calendars.json"].freshness == Freshness.STALE
    else:
        assert response.status_code == 503
        assert nthudata.states["/libraries/calendars.json"].freshness == Freshness.UNAVAILABLE


async def test_unknown_library_version_omits_aggregate_header(runtime, library_publisher):
    client, _, _ = runtime
    library_publisher.version = None
    response = await client.get("/calendars/")
    assert response.status_code == 200
    assert "X-Data-Commit-Hash" not in response.headers
