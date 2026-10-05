"""API discovery metadata without dataset or upstream dependencies."""

import httpx

from data_api.api.api import app
from data_api.data.manager import nthudata


async def test_metadata_available_without_datasets_or_upstream(monkeypatch):
    monkeypatch.setattr(nthudata, "states", {})

    async def unexpected_request(self, request):
        raise AssertionError("Metadata must not make upstream requests")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", unexpected_request)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as client:
        response = await client.get("/", headers={"Origin": "https://example.com"})

    assert response.status_code == 200
    assert response.json() == {
        "name": "NTHU Data API",
        "version": "2.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "mcp": "/mcp",
    }
    assert "location" not in response.headers
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert float(response.headers["X-Process-Time"]) >= 0
    assert nthudata.states == {}


async def test_metadata_matches_application_configuration(monkeypatch):
    monkeypatch.setattr(app, "title", "Test API")
    monkeypatch.setattr(app, "version", "9.8.7")
    monkeypatch.setattr(app, "openapi_schema", None)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        metadata = response.json()
        docs = await client.get(metadata["docs"])
        openapi = await client.get(metadata["openapi"])

    assert response.status_code == 200
    assert metadata["name"] == app.title
    assert metadata["version"] == app.version
    assert metadata["docs"] == app.docs_url
    assert metadata["openapi"] == app.openapi_url
    assert any(route.path == metadata["mcp"] for route in app.routes)
    assert docs.status_code == openapi.status_code == 200
    assert metadata["name"] == openapi.json()["info"]["title"]
    assert metadata["version"] == openapi.json()["info"]["version"]


async def test_metadata_hidden_from_openapi_and_swagger():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        schema = await client.get("/openapi.json")
        assert schema.status_code == 200
        assert "/" not in schema.json()["paths"]
        assert "/courses/" in schema.json()["paths"]
        assert "MetaResponse" not in schema.json()["components"]["schemas"]
        docs = await client.get("/docs")
        assert docs.status_code == 200
        assert "/openapi.json" in docs.text
        assert (await client.get("/")).status_code == 200
