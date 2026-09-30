"""Offline upstream fixtures for API smoke tests."""

import httpx
import pytest

from data_api.api.schemas.newsletters import NewsletterName
from data_api.data.manager import nthudata


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    async def unavailable(self, request):
        return httpx.Response(503, request=request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", unavailable)


@pytest.fixture
def mock_upstream(monkeypatch, no_external_network):
    def install(handler):
        transport = httpx.MockTransport(handler)

        async def handle_request(self, request):
            return await transport.handle_async_request(request)

        monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", handle_request)

    return install


@pytest.fixture
def library_space_payload():
    return {
        "resmsg": "成功",
        "rows": [
            {
                "spacetype": "1",
                "spacetypename": "Study room",
                "zoneid": "main",
                "zonename": "Main library",
                "count": "12",
            }
        ],
    }


@pytest.fixture
def lost_items_html():
    def make(count=12):
        header = "<tr><td>序號</td><td>拾獲時間</td><td>拾獲地點</td><td>描述</td></tr>"
        rows = "".join(
            f"<tr><td>{index}</td><td>2026-09-30</td><td>Main library</td>"
            "<td> Book\n  title </td></tr>"
            for index in range(count)
        )
        return f"<table>{header}{rows}</table>"

    return make


@pytest.fixture
def lost_items_empty_page():
    return '<div id="content"><h1>失物招領系統 Lost and Found System</h1>' "<br>目前無資料 !!</div>"


@pytest.fixture
async def dataset_runtime():
    data = {
        "/courses.json": [
            {"id": "11410TEST100000", "chinese_title": "Test course", "language": "中"}
        ],
        "/buses.json": {},
        "/calendars.json": [],
        "/announcements.json": [],
        "/announcements_list.json": [],
        "/dining.json": [],
        "/directory.json": [],
        "/newsletters.json": [
            {"name": name.value, "link": "https://example.com", "details": {}, "articles": []}
            for name in NewsletterName
        ],
        "/maps.json": {
            "main": {
                name: {"latitude": "24.79", "longitude": "120.99"}
                for name in ["校門", "綜合", "台積", "台達"]
            }
        },
    }

    def handler(request):
        if request.url.path == "/file_details.json":
            return httpx.Response(
                200,
                json={
                    "file_details": {
                        "/": [{"name": path.lstrip("/"), "last_commit": "fixture"} for path in data]
                    }
                },
            )
        if request.url.path in data:
            return httpx.Response(200, json=data[request.url.path])
        return httpx.Response(404)

    async with nthudata.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        yield nthudata
