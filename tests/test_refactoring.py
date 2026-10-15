"""Regression coverage for contract-preserving internal refactors."""

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from data_api.api import api
from data_api.core.config import PREFETCH_ENDPOINTS
from data_api.core.exceptions import UpstreamException
from data_api.data.nthudata import NTHUDataManager
from data_api.domain.buses.query import resolve_bus_time
from data_api.domain.buses.services import BusesService, PreparedBusData
from data_api.domain.courses.models import Conditions, CourseData
from data_api.domain.energy.services import EnergyService
from data_api.domain.libraries.services import LibrariesService
from data_api.runtime import Runtime, default_runtime, get_runtime


async def test_request_duration_uses_monotonic_clock(monkeypatch):
    clock = SimpleNamespace(
        time=Mock(side_effect=[100.0, 99.0]),
        perf_counter=Mock(side_effect=[10.0, 10.25]),
    )
    monkeypatch.setattr(api, "time", clock)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app), base_url="http://test"
    ) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Process-Time"] == "0.25"
    clock.time.assert_not_called()


@pytest.mark.parametrize(
    "day,time,instant,expected",
    [
        ("current", "23:59", "2026-10-16T23:59:00", ("weekday", "23:59")),
        ("current", "23:59", "2026-10-17T00:00:00", ("weekend", "00:00")),
        ("weekday", "09:03", "2026-10-17T00:00:00", ("weekday", "09:03")),
        ("weekend", None, "2026-10-19T00:00:00", ("weekend", "")),
    ],
)
def test_bus_time_resolution(day, time, instant, expected):
    now = datetime.fromisoformat(instant)
    state = resolve_bus_time(day, time, now)
    assert (state.day, state.after_time) == expected
    assert state.current_time == now.strftime("%H:%M")


def test_course_conditions_prepare_once_and_do_not_retain_course():
    conditions = Conditions(
        list_build_target=[{"row_field": "id", "matcher": "^A", "regex_match": True}]
    )
    first = CourseData.from_dict({"id": "A"})
    second = CourseData.from_dict({"id": "B"})
    assert conditions.accept(first)
    predicate = conditions._predicate
    assert not conditions.accept(second)
    assert conditions.accept(first)
    assert conditions._predicate is predicate
    assert not hasattr(conditions, "course")


async def _mcp_request(client, method, params):
    response = await client.post(
        "/mcp",
        headers={"Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    assert response.status_code == 200
    messages = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert len(messages) == 1
    assert "error" not in messages[0]
    return messages[0]["result"]


async def test_two_apps_isolate_snapshots_clients_and_mcp_http(mock_upstream):
    calls = []
    versions = {"first.test": "first", "second.test": "second"}
    payloads = {f"/{path}": [] for path in PREFETCH_ENDPOINTS}
    payloads.update(
        {
            "/buses.json": {},
            "/maps.json": {},
            "/libraries/rss.json": {
                "news": [],
                "eresources": [],
                "exhibit": [],
                "branches": [],
            },
        }
    )

    def handler(request):
        calls.append((request.url.host, request.url.path))
        marker = versions[request.url.host]
        if request.url.path == "/file_details.json":
            return httpx.Response(
                200,
                json={
                    "file_details": {
                        "/": [{"name": path, "version": marker} for path in PREFETCH_ENDPOINTS]
                    }
                },
            )
        if request.url.path == "/courses.json":
            return httpx.Response(200, json=[{"id": marker, "language": "中"}])
        return httpx.Response(200, json=payloads[request.url.path])

    mock_upstream(handler)
    first = api.create_app(Runtime.create(NTHUDataManager(base_url="https://first.test")))
    second = api.create_app(Runtime.create(NTHUDataManager(base_url="https://second.test")))
    assert first.state.runtime is not second.state.runtime
    assert first.state.mcp is not second.state.mcp
    assert first.state.runtime.courses.state is not second.state.runtime.courses.state
    async with first.router.lifespan_context(first):
        first_clients = (
            first.state.datasets.fetcher.client,
            first.state.runtime.energy.client,
            first.state.runtime.libraries.client,
        )
        assert all(client is not None and not client.is_closed for client in first_clients)
        async with second.router.lifespan_context(second):
            second_clients = (
                second.state.datasets.fetcher.client,
                second.state.runtime.energy.client,
                second.state.runtime.libraries.client,
            )
            assert all(a is not b for a, b in zip(first_clients, second_clients, strict=True))
            async with (
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=first), base_url="http://first"
                ) as first_rest,
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=second), base_url="http://second"
                ) as second_rest,
            ):
                before = len(calls)
                responses = await asyncio.gather(
                    first_rest.get("/courses"), second_rest.get("/courses")
                )
                for response, marker in zip(responses, ("first", "second"), strict=True):
                    assert response.json()[0]["id"] == marker
                    assert response.headers["X-Data-Commit-Hash"] == marker
                for rest, marker in ((first_rest, "first"), (second_rest, "second")):
                    initialized = await _mcp_request(
                        rest,
                        "initialize",
                        {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "runtime-test", "version": "1"},
                        },
                    )
                    assert initialized["serverInfo"]["version"] == first.version
                    result = await _mcp_request(
                        rest, "tools/call", {"name": "search_courses", "arguments": {}}
                    )
                    assert not result.get("isError", False)
                    assert json.loads(result["content"][0]["text"])["courses"][0]["id"] == marker
                    ping = await rest.get("/ping")
                    assert ping.status_code == 200
                    assert ping.json()["datasets"]["/courses.json"]["version"] == marker
                assert len(calls) == before
                assert get_runtime() is default_runtime
        assert all(client.is_closed for client in second_clients)
        assert all(not client.is_closed for client in first_clients)
    assert all(client.is_closed for client in first_clients)
    assert first.state.runtime.energy.client is None
    assert first.state.runtime.libraries.client is None
    assert not first.state.runtime.courses.state.usable
    assert not second.state.runtime.courses.state.usable
    assert first.state.runtime.courses.course_data == []
    assert first.state.runtime.buses._snapshot is None


async def test_runtime_closes_all_clients_on_startup_failure(monkeypatch):
    runtime = Runtime.create()
    application = api.create_app(runtime)
    clients = []

    async def fail(endpoints):
        clients.extend(
            [runtime.datasets.fetcher.client, runtime.energy.client, runtime.libraries.client]
        )
        raise RuntimeError("startup failed")

    monkeypatch.setattr(runtime.datasets, "prefetch", fail)
    with pytest.raises(RuntimeError, match="startup failed"):
        async with api.lifespan(application):
            pytest.fail("Startup must fail")
    assert len(clients) == 3
    assert all(client.is_closed for client in clients)
    assert runtime.datasets.fetcher.client is None
    assert runtime.energy.client is runtime.libraries.client is None


async def test_runtime_cannot_be_reentered_without_losing_live_clients():
    runtime = Runtime.create()
    async with runtime.lifespan():
        energy = runtime.energy.client
        library = runtime.libraries.client
        with pytest.raises(RuntimeError, match="already running"):
            async with runtime.lifespan():
                pytest.fail("Runtime must not be reentered")
        assert runtime.energy.client is energy
        assert runtime.libraries.client is library
        assert not energy.is_closed
        assert not library.is_closed


async def test_energy_reuses_one_injected_client():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, text='<img alt="kW: 1">')

    service = EnergyService()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service.client = client
        assert len(await service.get_realtime_electricity_usage()) == 3
        assert len(await service.get_realtime_electricity_usage()) == 3
        assert not client.is_closed
    assert len(requests) == 6


def test_bus_preparation_returns_data_without_runtime_state():
    data = BusesService.prepare({})
    assert isinstance(data, PreparedBusData)
    assert not isinstance(data, BusesService)
    assert not hasattr(data, "manager")
    assert not hasattr(data, "state")


def test_app_factory_defaults_to_independent_runtimes():
    first, second = api.create_app(), api.create_app()
    assert first.state.runtime is not second.state.runtime
    assert first.state.datasets is not second.state.datasets
    assert first.state.datasets is not default_runtime.datasets


async def test_isolated_app_reports_missing_snapshots_through_rest_and_mcp():
    application = api.create_app()
    async with application.router.lifespan_context(application):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://test"
        ) as client:
            response = await client.get("/courses", headers={"Origin": "https://example.com"})
            assert response.status_code == 503
            assert response.json() == {"detail": "Service temporarily unavailable"}
            assert response.headers["Access-Control-Allow-Origin"] == "*"
            assert float(response.headers["X-Process-Time"]) >= 0
            result = await _mcp_request(
                client, "tools/call", {"name": "search_courses", "arguments": {}}
            )
            assert result["isError"]
            assert "temporarily unavailable" in result["content"][0]["text"]
            assert "https://" not in result["content"][0]["text"]


async def test_energy_failure_cancels_siblings_before_releasing_client():
    started = []
    cancelled = []
    ready = asyncio.Event()

    async def handler(request):
        system = request.url.path
        started.append(system)
        if len(started) == 3:
            ready.set()
        await ready.wait()
        if system.endswith("1.aspx"):
            raise httpx.ConnectError("Unavailable", request=request)
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(system)

    service = EnergyService()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service.client = client
        with pytest.raises(UpstreamException):
            await service.get_realtime_electricity_usage()
        assert len(cancelled) == 2
        assert not client.is_closed


async def test_library_live_calls_borrow_the_injected_client(
    library_space_payload, lost_items_html
):
    methods = []

    def handler(request):
        methods.append(request.method)
        if request.method == "GET":
            return httpx.Response(200, json=library_space_payload)
        return httpx.Response(200, text=lost_items_html(count=1))

    service = LibrariesService()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service.client = client
        assert await service.get_space_availability() == library_space_payload["rows"]
        assert len(await service.get_lost_and_found_items()) == 1
        assert not client.is_closed
    assert methods == ["GET", "POST"]
