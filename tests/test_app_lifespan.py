"""Tests for the exported app's middleware, REST/MCP routes, and lifespans.

The data layer is stubbed to keep tests offline. Most tests also stub the MCP
lifespan: its real session manager can only start once per app. One integration
test exercises the real manager and HTTP transport through the exported app.
"""

import json
import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from data_api.api import api as api_module
from data_api.api.api import app
from data_api.core import config
from data_api.data.manager import nthudata
from data_api.domain.buses import services as buses_services
from data_api.domain.courses import services as courses_services


@asynccontextmanager
async def _noop_lifespan(app):
    """Stand in for the MCP lifespan, which cannot be started twice."""
    yield


class TestCombinedLifespan:
    """Tests for the startup tasks chained into the combined lifespan."""

    async def test_runs_startup_tasks_in_order(self, monkeypatch):
        """Test the combined lifespan pre-fetches data and updates both services."""
        calls = []

        async def fake_prefetch(endpoints):
            calls.append(("prefetch", list(endpoints)))
            return {endpoint: True for endpoint in endpoints}

        async def fake_buses_update():
            calls.append(("buses", None))

        async def fake_courses_update():
            calls.append(("courses", None))

        monkeypatch.setattr(api_module, "mcp_app", SimpleNamespace(lifespan=_noop_lifespan))
        monkeypatch.setattr(nthudata, "prefetch", fake_prefetch)
        monkeypatch.setattr(buses_services.buses_service, "update_data", fake_buses_update)
        monkeypatch.setattr(courses_services.courses_service, "update_data", fake_courses_update)

        async with api_module.combined_lifespan(app):
            pass

        assert [name for name, _ in calls] == ["prefetch", "buses", "courses"]
        assert calls[0][1] == config.PREFETCH_ENDPOINTS

    async def test_reports_failed_endpoints_as_ascii(self, monkeypatch, caplog):
        """Lifecycle logs stay ASCII and summarize partial availability."""

        async def fake_prefetch(endpoints):
            return {endpoint: index == 0 for index, endpoint in enumerate(endpoints)}

        async def noop():
            return None

        monkeypatch.setattr(api_module, "mcp_app", SimpleNamespace(lifespan=_noop_lifespan))
        monkeypatch.setattr(nthudata, "prefetch", fake_prefetch)
        monkeypatch.setattr(buses_services.buses_service, "update_data", noop)
        monkeypatch.setattr(courses_services.courses_service, "update_data", noop)

        with caplog.at_level(logging.INFO):
            async with api_module.combined_lifespan(app):
                pass
        assert f"Data startup: 1/{len(config.PREFETCH_ENDPOINTS)} datasets usable" in caplog.text
        caplog.text.encode("ascii")

    @pytest.mark.parametrize("startup_fails", [False, True])
    async def test_exported_lifespan_orders_and_unwinds_contexts(self, monkeypatch, startup_fails):
        calls = []

        @asynccontextmanager
        async def fake_mcp_lifespan(application):
            assert application is app
            calls.append("mcp startup")
            try:
                yield
            finally:
                calls.append("mcp shutdown")

        @asynccontextmanager
        async def fake_data_lifespan(application):
            assert application is app
            calls.append("data startup")
            if startup_fails:
                raise RuntimeError("startup failed")
            try:
                yield
            finally:
                calls.append("data shutdown")

        monkeypatch.setattr(api_module, "mcp_app", SimpleNamespace(lifespan=fake_mcp_lifespan))
        monkeypatch.setattr(api_module, "lifespan", fake_data_lifespan)

        if startup_fails:
            with pytest.raises(RuntimeError, match="startup failed"):
                async with app.router.lifespan_context(app):
                    pass
            assert calls == ["mcp startup", "data startup", "mcp shutdown"]
        else:
            async with app.router.lifespan_context(app):
                assert calls == ["mcp startup", "data startup"]
            assert calls == ["mcp startup", "data startup", "data shutdown", "mcp shutdown"]


FAKE_COURSE = {
    "id": "11410TEST100000",
    "chinese_title": "測試課程",
    "english_title": "Test Course",
    "credit": "3",
    "size_limit": "50",
    "freshman_reservation": "0",
    "object": "",
    "ge_type": "",
    "language": "中",
    "note": "",
    "suspend": "",
    "class_room_and_time": "T3T4",
    "teacher": "測試教師",
    "prerequisite": "",
    "limit_note": "",
    "expertise": "",
    "program": "",
    "no_extra_selection": "",
    "required_optional_note": "",
}


async def _fake_fetch(url: str, sha256=None):
    """Serve in-memory data in place of a request to data.nthusa.tw."""
    if url.endswith("file_details.json"):
        return {
            "file_details": {
                "/": [
                    {"name": name, "last_commit": "testcommithash"}
                    for name in config.PREFETCH_ENDPOINTS
                ]
            }
        }
    if url.endswith("courses.json"):
        return [FAKE_COURSE]
    if url.endswith("buses.json"):
        return {}
    return []


class TestCoursesAfterStartup:
    """Tests that the app's own lifespan is attached to the app that gets served."""

    async def test_courses_endpoint_returns_data_after_startup(self, monkeypatch):
        """Test /courses/ is populated once the app's own lifespan has run.

        Exercise actual validation and conversion against a fixed upstream response.
        """
        monkeypatch.setattr(api_module, "mcp_app", SimpleNamespace(lifespan=_noop_lifespan))
        monkeypatch.setattr(nthudata.fetcher, "fetch_json", _fake_fetch)
        monkeypatch.setattr(courses_services.courses_service, "course_data", [])

        async with app.router.lifespan_context(app):
            assert courses_services.courses_service.course_data, "courses data was not loaded"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
            ) as client:
                response = await client.get("/courses/")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["chinese_title"] == "測試課程"


def test_exported_app_serves_rest_and_mcp_with_middleware(monkeypatch):
    """Start the real ASGI app and MCP manager without external data access."""

    async def fake_prefetch(endpoints):
        return {endpoint: True for endpoint in endpoints}

    async def noop():
        return None

    monkeypatch.setattr(nthudata, "prefetch", fake_prefetch)
    monkeypatch.setattr(nthudata.fetcher, "fetch_json", _fake_fetch)
    monkeypatch.setattr(buses_services.buses_service, "update_data", noop)
    monkeypatch.setattr(courses_services.courses_service, "course_data", [])
    monkeypatch.setattr(courses_services.courses_service, "last_commit_hash", None)
    origin = "https://example.com"

    with TestClient(app) as client:
        response = client.get("/courses/", headers={"Origin": origin})
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == [FAKE_COURSE["id"]]
        assert float(response.headers["X-Process-Time"]) >= 0
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert response.headers["X-Total-Count"] == "1"
        assert response.headers["X-Data-Commit-Hash"] == "testcommithash"
        exposed = {
            header.strip().lower()
            for header in response.headers["Access-Control-Expose-Headers"].split(",")
        }
        assert {"x-total-count", "x-data-commit-hash", "x-process-time"} <= exposed

        for path, method in [("/courses/", "GET"), ("/mcp", "POST")]:
            response = client.options(
                path,
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": method,
                    "Access-Control-Request-Headers": "Content-Type, MCP-Protocol-Version",
                },
            )
            assert response.status_code == 200
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert method in response.headers["Access-Control-Allow-Methods"]
            assert (
                "mcp-protocol-version" in response.headers["Access-Control-Allow-Headers"].lower()
            )
            assert float(response.headers["X-Process-Time"]) >= 0

        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "/courses/search" in response.json()["paths"]

        for method, params in [
            (
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "phase-a-test", "version": "1.0"},
                },
            ),
            ("tools/list", {}),
            ("tools/call", {"name": "search_courses", "arguments": {"limit": 1}}),
        ]:
            response = client.post(
                "/mcp",
                headers={
                    "Origin": origin,
                    "Accept": "application/json, text/event-stream",
                },
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            )
            assert response.status_code == 200
            assert float(response.headers["X-Process-Time"]) >= 0
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            messages = [
                json.loads(line.removeprefix("data: "))
                for line in response.text.splitlines()
                if line.startswith("data: ")
            ]
            assert len(messages) == 1
            assert "error" not in messages[0]
            result = messages[0]["result"]
            if method == "initialize":
                assert "serverInfo" in result
            elif method == "tools/list":
                assert "search_courses" in {tool["name"] for tool in result["tools"]}
            else:
                assert not result.get("isError", False)
                content = json.loads(result["content"][0]["text"])
                assert content["count"] == 1
                assert content["courses"][0]["id"] == FAKE_COURSE["id"]
