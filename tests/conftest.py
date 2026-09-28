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
async def dataset_runtime():
    data = {
        "/courses.json": [
            {"id": "11410TEST100000", "chinese_title": "Test course", "language": "中"}
        ],
        "/buses.json": {},
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
