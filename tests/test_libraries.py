"""Tests for libraries endpoints."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.domain.libraries import services
from data_api.domain.libraries.services import filter_calendar_events, get_event_date_range

RSS_DATA = {
    "news": [
        {
            "guid": "1",
            "category": "最新消息",
            "title": "Library news",
            "link": "https://www.lib.nthu.edu.tw/news/1",
            "pubDate": "Mon, 22 Sep 2025 10:00:00 +0800",
            "description": "hello",
            "author": "NTHU Library",
            "image": {
                "url": "https://www.lib.nthu.edu.tw/image/news/1.jpg",
                "title": "cover",
                "link": "https://www.lib.nthu.edu.tw/",
            },
        }
    ],
    # The scraper emits null for missing RSS tags, including items without an image.
    "eresources": [
        {
            "guid": None,
            "category": None,
            "title": "No image",
            "link": None,
            "pubDate": None,
            "description": "",
            "author": None,
            "image": None,
        }
    ],
}


def make_event(event_id, title, start, end, all_day, description=None):
    return {
        "id": event_id,
        "title": title,
        "description": description,
        "start": start,
        "end": end,
        "all_day": all_day,
    }


EVENTS = [
    make_event(
        "a1", "08:00-22:00", "2025-09-24T08:00:00+08:00", "2025-09-24T22:00:00+08:00", False
    ),
    make_event("a2", "休館", "2025-09-25", "2025-09-26", True, "中秋節"),
    make_event("a3", "寒假閉館", "2026-01-20", "2026-01-23", True),
    make_event("a4", "Overnight", "2026-02-01T22:00:00+08:00", "2026-02-02T00:00:00+08:00", False),
]

CALENDARS_DATA = [
    {
        "id": "main",
        "name": "總圖書館開館時間",
        "description": None,
        "timezone": "Asia/Taipei",
        "url": "https://calendar.google.com/calendar/embed?src=main",
        "events": EVENTS,
    },
    {
        "id": "hss",
        "name": "人社分館開館時間",
        "description": None,
        "timezone": "Asia/Taipei",
        "url": "https://calendar.google.com/calendar/embed?src=hss",
        "events": [],
    },
]

FAKE_DATA = {
    services.RSS_JSON_PATH: RSS_DATA,
    services.CALENDARS_JSON_PATH: CALENDARS_DATA,
}


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
def fake_data(monkeypatch):
    """Serve the scraper JSON files from memory instead of data.nthusa.tw."""

    async def fake_get(endpoint_name):
        if endpoint_name in FAKE_DATA:
            return "fakehash", FAKE_DATA[endpoint_name]
        return None

    monkeypatch.setattr(services.nthudata, "get", fake_get)


@pytest.fixture
def no_data(monkeypatch):
    """Simulate data.nthusa.tw being unavailable."""

    async def fake_get(endpoint_name):
        return None

    monkeypatch.setattr(services.nthudata, "get", fake_get)


class TestEventFiltering:
    """Tests for event date handling and filtering."""

    def test_all_day_end_is_exclusive(self):
        assert get_event_date_range(EVENTS[2]) == (date(2026, 1, 20), date(2026, 1, 22))

    def test_timed_event(self):
        assert get_event_date_range(EVENTS[0]) == (date(2025, 9, 24), date(2025, 9, 24))

    def test_timed_event_ending_at_midnight(self):
        assert get_event_date_range(EVENTS[3]) == (date(2026, 2, 1), date(2026, 2, 1))

    def test_filter_by_date_range(self):
        events = filter_calendar_events(EVENTS, start=date(2025, 9, 25), end=date(2026, 1, 21))
        assert [e["id"] for e in events] == ["a2", "a3"]

    def test_filter_by_keyword_matches_description(self):
        events = filter_calendar_events(EVENTS, keyword="中秋")
        assert [e["id"] for e in events] == ["a2"]

    def test_filter_keyword_is_case_insensitive(self):
        events = filter_calendar_events(EVENTS, keyword="overnight")
        assert [e["id"] for e in events] == ["a4"]


class TestLibraryRss:
    """Tests for the RSS endpoint backed by the scraper JSON."""

    async def test_get_rss(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/rss/news")
        assert response.status_code == 200
        assert response.headers["X-Data-Commit-Hash"] == "fakehash"
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Library news"

    async def test_nullable_fields(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/rss/eresources")
        assert response.status_code == 200
        assert response.json()[0]["image"] is None

    async def test_missing_feed(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/rss/exhibit")
        assert response.status_code == 404

    async def test_invalid_type(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/rss/unknown")
        assert response.status_code == 422

    async def test_data_unavailable(self, client: AsyncClient, no_data):
        response = await client.get("/libraries/rss/news")
        assert response.status_code == 503


class TestLibraryCalendars:
    """Tests for the calendar endpoints."""

    async def test_list_calendars_without_events(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars")
        assert response.status_code == 200
        data = response.json()
        assert [c["id"] for c in data] == ["main", "hss"]
        assert all("events" not in c for c in data)

    async def test_get_calendar(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/main")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "總圖書館開館時間"
        assert "events" not in data

    async def test_calendar_missing_from_data(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/nanda")
        assert response.status_code == 404

    async def test_invalid_calendar_id(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/unknown")
        assert response.status_code == 422

    async def test_list_events(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/main/events")
        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "4"
        assert [e["id"] for e in response.json()] == ["a1", "a2", "a3", "a4"]

    async def test_events_on_a_single_day(self, client: AsyncClient, fake_data):
        response = await client.get(
            "/libraries/calendars/main/events", params={"start": "2025-09-25", "end": "2025-09-25"}
        )
        assert response.status_code == 200
        assert [e["id"] for e in response.json()] == ["a2"]

    async def test_events_by_keyword(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/main/events", params={"keyword": "閉館"})
        assert [e["id"] for e in response.json()] == ["a3"]

    async def test_events_pagination(self, client: AsyncClient, fake_data):
        response = await client.get(
            "/libraries/calendars/main/events", params={"limit": 2, "offset": 1}
        )
        assert response.headers["X-Total-Count"] == "4"
        assert [e["id"] for e in response.json()] == ["a2", "a3"]

    async def test_events_invalid_range(self, client: AsyncClient, fake_data):
        response = await client.get(
            "/libraries/calendars/main/events", params={"start": "2025-10-01", "end": "2025-09-01"}
        )
        assert response.status_code == 400

    async def test_events_invalid_date(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/main/events", params={"start": "soon"})
        assert response.status_code == 422

    async def test_events_of_missing_calendar(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/nanda/events")
        assert response.status_code == 404

    async def test_get_event(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/main/events/a2")
        assert response.status_code == 200
        assert response.json()["title"] == "休館"

    async def test_get_missing_event(self, client: AsyncClient, fake_data):
        response = await client.get("/libraries/calendars/main/events/nope")
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "url",
        [
            "/libraries/calendars",
            "/libraries/calendars/main",
            "/libraries/calendars/main/events",
            "/libraries/calendars/main/events/a1",
        ],
    )
    async def test_data_unavailable(self, client: AsyncClient, no_data, url: str):
        response = await client.get(url)
        assert response.status_code == 503


class TestLibrariesLiveEndpoints:
    """Endpoints that still hit the library website directly."""

    @pytest.mark.parametrize(
        "url",
        ["/libraries/space", "/libraries/lost_and_found"],
    )
    async def test_libraries_endpoints(self, client: AsyncClient, url: str):
        """Accept 200 or 500 since the library service may be unavailable."""
        response = await client.get(url)
        assert response.status_code in [200, 500]
