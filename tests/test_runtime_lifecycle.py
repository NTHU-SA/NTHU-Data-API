"""Production REST/MCP wiring, startup, shutdown and runtime refresh."""

import httpx
import pytest
from fastmcp import Client
from test_data_manager import Clock, Publisher

from data_api.api import api as api_module
from data_api.data.manager import nthudata
from data_api.data.nthudata import Freshness
from data_api.domain.courses.services import courses_service
from data_api.mcp.server import mcp


async def test_rest_and_mcp_observe_runtime_course_refresh(monkeypatch):
    clock = Clock()
    publisher = Publisher(
        [{"id": "A", "english_title": "Version A", "language": "中"}], "courses.json"
    )
    monkeypatch.setattr(nthudata, "clock", clock)
    async with nthudata.lifespan(publisher.client()):
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=api_module.app), base_url="http://test"
            ) as rest,
            Client(mcp) as tools,
        ):
            first = await rest.get("/courses/")
            assert first.json()[0]["id"] == "A"
            assert first.headers["X-Data-Commit-Hash"] == "a"
            publisher.version, publisher.payload = "b", [
                {"id": "B", "english_title": "Version B", "language": "中"}
            ]
            clock.advance()
            second = await rest.get("/courses/search?english_title=Version")
            assert second.json()[0]["id"] == "B"
            assert second.headers["X-Data-Commit-Hash"] == "b"
            result = await tools.call_tool("search_courses", {})
            assert result.data["courses"][0]["id"] == "B"
            assert courses_service.state is nthudata.states["/courses.json"]
            assert courses_service.course_data is courses_service.state.snapshot.data
            assert publisher.calls.count("/courses.json") == 2

            publisher.version, publisher.payload = "c", [{"id": "C", "language": "中"}]
            clock.advance()
            result = await tools.call_tool("search_courses", {})
            assert result.data["courses"][0]["id"] == "C"
            assert (await rest.get("/courses/")).json()[0]["id"] == "C"
            publisher.version, publisher.data_error = "d", 503
            clock.advance()
            fallback = await rest.get("/courses/")
            assert fallback.status_code == 200
            assert fallback.json()[0]["id"] == "C"
            assert fallback.headers["X-Data-Commit-Hash"] == "c"
            assert courses_service.state.freshness == Freshness.STALE


@pytest.mark.parametrize("empty", [True, False])
async def test_cold_start_empty_is_not_unavailable(empty):
    publisher = Publisher([], "courses.json")
    if not empty:
        publisher.data_error = 503
    async with nthudata.lifespan(publisher.client()):
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=api_module.app), base_url="http://test"
            ) as rest,
            Client(mcp) as tools,
        ):
            response = await rest.get("/courses/")
            result = await tools.call_tool("search_courses", {}, raise_on_error=False)
            if empty:
                assert response.status_code == 200
                assert response.json() == []
                assert not result.is_error
                assert result.data == {"count": 0, "courses": []}
            else:
                assert response.status_code == 503
                assert response.json() == {"detail": "Service temporarily unavailable"}
                assert result.is_error
                assert "temporarily unavailable" in result.content[0].text
                assert "Traceback" not in result.content[0].text
                assert "http" not in result.content[0].text


@pytest.mark.parametrize(
    "endpoint,path,payload,tool,args",
    [
        ("dining.json", "/dining/", [], "find_dining", {}),
        ("announcements.json", "/announcements/", [], "get_announcements", {}),
        ("newsletters.json", "/newsletters/", [], "get_newsletters", {}),
        ("buses.json", "/buses/routes", {}, "get_next_buses", {}),
    ],
)
async def test_other_datasets_empty_unversioned_and_unavailable(
    endpoint, path, payload, tool, args
):
    publisher = Publisher(payload, endpoint)
    publisher.version = None
    async with nthudata.lifespan(publisher.client()):
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=api_module.app), base_url="http://test"
            ) as rest,
            Client(mcp) as tools,
        ):
            response = await rest.get(path)
            assert response.status_code == 200
            assert "X-Data-Commit-Hash" not in response.headers
            assert not (await tools.call_tool(tool, args)).is_error
    publisher.data_error = 503
    async with nthudata.lifespan(publisher.client()):
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=api_module.app), base_url="http://test"
            ) as rest,
            Client(mcp) as tools,
        ):
            assert (await rest.get(path)).status_code == 503
            result = await tools.call_tool(tool, args, raise_on_error=False)
            assert result.is_error
            assert "temporarily unavailable" in result.content[0].text


@pytest.mark.parametrize("upstream_available", [True, False])
async def test_real_data_lifespan_client_cleanup(monkeypatch, upstream_available):
    publisher = Publisher([{"id": "A", "language": "中"}], "courses.json")
    if not upstream_available:
        publisher.data_error = 503

    async def handler(self, request):
        return await publisher(request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", handler)
    async with api_module.lifespan(api_module.app):
        client = nthudata.fetcher.client
        assert client is not None
        assert not client.is_closed
        assert api_module.app.state.datasets is nthudata
        assert courses_service.state.usable is upstream_available
        if upstream_available:
            assert client.timeout.read == 15
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api_module.app), base_url="http://test"
        ) as rest:
            assert (await rest.get("/courses/")).status_code == (200 if upstream_available else 503)
    assert client.is_closed
    assert nthudata.fetcher.client is None
    assert not courses_service.state.usable


async def test_app_startup_exception_closes_client(monkeypatch):
    client = None

    async def fail(endpoints):
        nonlocal client
        client = nthudata.fetcher.client
        raise RuntimeError("unexpected startup bug")

    monkeypatch.setattr(nthudata, "prefetch", fail)
    with pytest.raises(RuntimeError, match="startup bug"):
        async with api_module.lifespan(api_module.app):
            pass
    assert client is not None
    assert client.is_closed
    assert nthudata.fetcher.client is None
