"""Offline readiness diagnostics and schema visibility."""

from dataclasses import replace
from datetime import datetime, timezone

import httpx
import pytest
from test_data_manager import Clock

from data_api.api import api as api_module
from data_api.core.config import PREFETCH_ENDPOINTS
from data_api.data.manager import nthudata
from data_api.data.nthudata import Freshness, RefreshError

EXPECTED_DATASETS = {
    "/announcements.json",
    "/announcements_list.json",
    "/buses.json",
    "/calendars.json",
    "/courses.json",
    "/dining.json",
    "/directory.json",
    "/libraries/calendars.json",
    "/libraries/rss.json",
    "/maps.json",
    "/newsletters.json",
}


@pytest.fixture
async def ping_runtime(monkeypatch):
    clock = Clock()
    calls = []
    payloads = {
        path: {} if path in {"/buses.json", "/maps.json", "/libraries/rss.json"} else []
        for path in EXPECTED_DATASETS
    }

    async def handler(self, request):
        path = request.url.path
        calls.append(path)
        if path == "/file_details.json":
            return httpx.Response(
                200,
                json={
                    "file_details": {
                        "/": [
                            {"name": name.lstrip("/"), "last_commit": "fixture"}
                            for name in payloads
                        ]
                    }
                },
            )
        if path == "/libraries.json":
            return httpx.Response(
                200,
                content=b"<!doctype html><html><body>Index</body></html>",
                headers={"Content-Type": "text/html"},
            )
        return httpx.Response(200, json=payloads[path])

    monkeypatch.setattr(nthudata, "clock", clock)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", handler)
    async with api_module.lifespan(api_module.app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api_module.app), base_url="http://test"
        ) as client:
            yield client, clock, calls


async def test_ping_ready_after_startup_including_empty_datasets(ping_runtime):
    client, _, calls = ping_runtime
    assert "/libraries.json" not in calls
    assert {f"/{path}" for path in PREFETCH_ENDPOINTS} == EXPECTED_DATASETS
    assert EXPECTED_DATASETS <= set(calls)
    calls_before = list(calls)

    response = await client.get("/ping", headers={"Origin": "https://example.com"})

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert float(response.headers["X-Process-Time"]) >= 0
    report = response.json()
    assert report["status"] == "ok"
    assert report["ready"] is True
    assert datetime.fromisoformat(report["checked_at"]).utcoffset().total_seconds() == 0
    assert set(report["datasets"]) == EXPECTED_DATASETS
    for path, health in report["datasets"].items():
        state = nthudata.states[path]
        assert health == {
            "usable": True,
            "freshness": "current",
            "check_due": False,
            "version": "fixture",
            "loaded_at": state.snapshot.loaded_at.isoformat().replace("+00:00", "Z"),
            "published_at": None,
            "last_checked_at": state.last_checked_at.isoformat().replace("+00:00", "Z"),
            "last_refresh_attempt_at": (
                state.last_refresh_attempt_at.isoformat().replace("+00:00", "Z")
            ),
            "last_refresh_success_at": (
                state.last_refresh_success_at.isoformat().replace("+00:00", "Z")
            ),
            "last_error": None,
        }
    assert calls == calls_before


@pytest.mark.parametrize(
    "condition,expected_status",
    [
        ("ready", 200),
        ("stale", 200),
        ("unverified", 200),
        ("expired", 200),
        ("missing", 503),
        ("unregistered", 503),
        ("cold", 503),
    ],
)
async def test_ping_head_matches_readiness_without_refresh(
    ping_runtime, monkeypatch, condition, expected_status
):
    client, clock, calls = ping_runtime
    path = "/libraries/rss.json"
    state = nthudata.states[path]
    if condition in {"stale", "unverified"}:
        state.freshness = Freshness(condition)
    elif condition == "expired":
        clock.advance(nthudata.ttl)
    elif condition == "missing":
        state.snapshot = None
        state.freshness = Freshness.UNAVAILABLE
    elif condition == "unregistered":
        monkeypatch.delitem(nthudata.states, path)
    elif condition == "cold":
        monkeypatch.setattr(nthudata, "states", {})
    calls_before = list(calls)
    states_before = {
        path: (state.snapshot, state.freshness, state.next_check)
        for path, state in nthudata.states.items()
    }

    response = await client.head("/ping", headers={"Origin": "https://example.com"})
    get_response = await client.get("/ping")

    assert response.status_code == get_response.status_code == expected_status
    assert response.content == b""
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Content-Type"] == get_response.headers["Content-Type"]
    assert "Content-Length" not in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert float(response.headers["X-Process-Time"]) >= 0
    assert calls == calls_before
    assert {
        path: (state.snapshot, state.freshness, state.next_check)
        for path, state in nthudata.states.items()
    } == states_before


async def test_ping_head_sends_no_asgi_body(ping_runtime):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await api_module.app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "HEAD",
            "scheme": "http",
            "path": "/ping",
            "raw_path": b"/ping",
            "query_string": b"",
            "headers": [],
            "server": ("test", 80),
            "client": ("test", 123),
        },
        receive,
        send,
    )

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 200
    bodies = [message for message in sent if message["type"] == "http.response.body"]
    assert bodies
    assert all(message.get("body", b"") == b"" for message in bodies)


async def test_ping_head_cors_preflight(ping_runtime):
    client, _, calls = ping_runtime
    calls_before = list(calls)

    response = await client.options(
        "/ping",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "HEAD",
        },
    )

    assert response.status_code == 200
    assert "HEAD" in response.headers["Access-Control-Allow-Methods"]
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert calls == calls_before


@pytest.mark.parametrize("freshness", [Freshness.STALE, Freshness.UNVERIFIED])
async def test_ping_keeps_usable_fallback_ready(ping_runtime, freshness):
    client, _, calls = ping_runtime
    state = nthudata.states["/courses.json"]
    now = datetime.now(timezone.utc)
    state.freshness = freshness
    state.last_error = RefreshError("http_status", now, 502)
    state.snapshot = replace(state.snapshot, published_at="2026-09-29T08:00:00+08:00")
    calls_before = list(calls)

    response = await client.get("/ping")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["status"] == "degraded"
    health = response.json()["datasets"]["/courses.json"]
    assert health["freshness"] == freshness
    assert health["usable"] is True
    assert health["published_at"] == "2026-09-29T08:00:00+08:00"
    assert health["last_error"] == {
        "category": "http_status",
        "at": now.isoformat().replace("+00:00", "Z"),
        "status_code": 502,
    }
    assert state.freshness == freshness
    assert calls == calls_before


async def test_ping_expired_check_does_not_refresh_or_mutate(ping_runtime):
    client, clock, calls = ping_runtime
    clock.advance(nthudata.ttl)
    calls_before = list(calls)
    snapshots = {path: state.snapshot for path, state in nthudata.states.items()}

    for _ in range(2):
        response = await client.get("/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        for health in response.json()["datasets"].values():
            assert health["freshness"] == "current"
            assert health["check_due"] is True
    assert calls == calls_before
    assert all(state.snapshot is snapshots[path] for path, state in nthudata.states.items())


@pytest.mark.parametrize("never_registered", [True, False])
async def test_ping_missing_dataset_is_unavailable(ping_runtime, monkeypatch, never_registered):
    client, _, calls = ping_runtime
    path = "/libraries/rss.json"
    state = nthudata.states[path]
    if never_registered:
        monkeypatch.delitem(nthudata.states, path)
    else:
        state.snapshot = None
        state.freshness = Freshness.UNAVAILABLE
        state.last_error = RefreshError("timeout", datetime.now(timezone.utc))
    calls_before = list(calls)

    response = await client.get("/ping")

    assert response.status_code == 503
    assert response.headers["Cache-Control"] == "no-store"
    report = response.json()
    assert report["status"] == "unavailable"
    assert report["ready"] is False
    health = report["datasets"][path]
    assert health["usable"] is False
    assert health["freshness"] == "unavailable"
    assert health["version"] is None
    assert health["loaded_at"] is None
    if never_registered:
        assert health["check_due"] is True
        assert health["last_checked_at"] is None
        assert health["last_error"] is None
        assert path not in nthudata.states
    else:
        assert health["last_error"]["category"] == "timeout"
        assert health["last_error"]["status_code"] is None
    assert calls == calls_before


async def test_ping_reports_additional_registered_datasets(ping_runtime, monkeypatch):
    client, _, _ = ping_runtime
    monkeypatch.setattr(nthudata, "states", dict(nthudata.states))
    nthudata.state_for("extra.json")

    response = await client.get("/ping")

    assert response.status_code == 503
    assert response.json()["datasets"]["/extra.json"]["usable"] is False


async def test_ping_cold_registry_is_not_ready(monkeypatch):
    monkeypatch.setattr(nthudata, "states", {})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api_module.app), base_url="http://test"
    ) as client:
        response = await client.get("/ping")
    assert response.status_code == 503
    assert set(response.json()["datasets"]) == EXPECTED_DATASETS
    assert all(not health["usable"] for health in response.json()["datasets"].values())
    assert nthudata.states == {}


async def test_ping_hidden_from_openapi_and_swagger(ping_runtime):
    client, _, _ = ping_runtime
    schema = await client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/ping" not in schema.json()["paths"]
    assert "/courses/" in schema.json()["paths"]
    assert "PingResponse" not in schema.json()["components"]["schemas"]
    docs = await client.get("/docs")
    assert docs.status_code == 200
    assert "/openapi.json" in docs.text
    assert "/ping" not in docs.text
    assert (await client.get("/ping")).status_code == 200
    assert (await client.head("/ping")).status_code == 200
