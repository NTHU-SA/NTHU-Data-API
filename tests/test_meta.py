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


def test_metadata_openapi_schema():
    schema = app.openapi()
    operation = schema["paths"]["/"]["get"]
    assert operation["operationId"] == "getApiMetadata"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/MetaResponse"
    }
    metadata_schema = schema["components"]["schemas"]["MetaResponse"]
    fields = {"name", "version", "docs", "openapi", "mcp"}
    assert set(metadata_schema["required"]) == fields
    assert set(metadata_schema["properties"]) == fields
    assert all(field["type"] == "string" for field in metadata_schema["properties"].values())
