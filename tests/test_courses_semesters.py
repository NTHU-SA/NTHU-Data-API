"""Semester discovery, request-local snapshots, failures and REST/MCP consistency."""

import asyncio
import hashlib
import json
from collections import Counter
from contextlib import asynccontextmanager
from urllib.parse import quote

import httpx
import pytest
from conftest import course_payload
from fastmcp import Client
from test_data_manager import Clock

from data_api.api.api import create_app
from data_api.data.nthudata import Freshness, NTHUDataManager
from data_api.runtime import Runtime


class SemesterPublisher:
    def __init__(self):
        self.clock = Clock()
        self.calls = Counter()
        self.errors = {}
        self.catalog = ["11420", "11510"]
        self.documents = {
            "/courses/latest.json": [course_payload(id="11510LATEST")],
            "/courses/semesters/11420.json": [
                course_payload(
                    id="11420OLD",
                    semester_code="11420",
                    language_code=None,
                    lecturers=[{"label": "Old [AI]"}],
                    credits=0.5,
                    meetings=[{"classroom": None, "time": "bad", "time_codes": None}],
                    parsing_issues=["Unrecognized time code"],
                )
            ],
            "/courses/semesters/11510.json": [
                course_payload(id="11510NEW", lecturers=[{"name_zh": "老師", "name_en": "Teacher"}])
            ],
        }
        self.version = "a"

    async def __call__(self, request):
        path = request.url.path
        self.calls[path] += 1
        if path in self.errors:
            error = self.errors[path]
            if isinstance(error, Exception):
                raise error
            return httpx.Response(error)
        docs = self.documents | {"/courses/sources.json": {"semesters": self.catalog}}
        if path == "/file_details.json":
            return httpx.Response(
                200,
                json={
                    "file_details": {
                        "/": [
                            {
                                "name": name[1:],
                                "last_commit": self.version + name,
                                "sha256": hashlib.sha256(json.dumps(data).encode()).hexdigest(),
                            }
                            for name, data in docs.items()
                        ]
                    }
                },
            )
        if path not in docs:
            return httpx.Response(404)
        return httpx.Response(200, content=json.dumps(docs[path]).encode())

    @asynccontextmanager
    async def clients(self):
        runtime = Runtime.create(NTHUDataManager(clock=self.clock))
        app = create_app(runtime)
        async with runtime.datasets.lifespan(
            httpx.AsyncClient(transport=httpx.MockTransport(self))
        ):
            async with (
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as rest,
                Client(app.state.mcp) as mcp,
            ):
                yield runtime, rest, mcp


async def test_discovery_and_default_latest_use_independent_versions():
    publisher = SemesterPublisher()
    async with publisher.clients() as (runtime, rest, mcp):
        catalog = await rest.get("/courses/semesters")
        assert catalog.status_code == 200
        assert catalog.json() == ["11510", "11420"]
        assert catalog.headers["X-Total-Count"] == "2"
        assert catalog.headers["X-Data-Commit-Hash"] == "a/courses/sources.json"
        latest = await rest.get("/courses")
        named = await rest.get("/courses/11510")
        assert latest.json()[0]["id"] == "11510LATEST"
        assert named.json()[0]["id"] == "11510NEW"
        assert latest.headers["X-Data-Commit-Hash"] == "a/courses/latest.json"
        assert named.headers["X-Data-Commit-Hash"] == "a/courses/semesters/11510.json"
        for semester, expected in [("11420", "11420OLD"), ("11510", "11510NEW")]:
            got = await rest.get(f"/courses/{semester}")
            post = await rest.post(f"/courses/{semester}/query", json=[])
            tool = await mcp.call_tool("search_courses", {"semester": semester})
            assert got.json() == post.json() == tool.data["courses"]
            assert got.json()[0]["id"] == expected
            assert len(got.json()[0]) == 33
        assert publisher.calls["/courses/semesters/11420.json"] == 1
        assert publisher.calls["/courses/semesters/11510.json"] == 1
        assert runtime.datasets.states["/courses/semesters/11420.json"].usable


@pytest.mark.parametrize("semester", ["bad", "1151", "115100", "１１５１０", "11510x", "11510\n"])
async def test_invalid_semester_is_rejected_without_upstream_calls(semester):
    publisher = SemesterPublisher()
    async with publisher.clients() as (runtime, rest, mcp):
        for method, suffix, kwargs in [("GET", "", {}), ("POST", "/query", {"json": []})]:
            response = await rest.request(
                method, f"/courses/{quote(semester, safe='')}{suffix}", **kwargs
            )
            assert response.status_code == 422
        result = await mcp.call_tool("search_courses", {"semester": semester}, raise_on_error=False)
        assert result.is_error
        assert not publisher.calls
        assert not any("/semesters/" in path for path in runtime.datasets.states)


async def test_unknown_and_unavailable_semesters_do_not_fall_back():
    publisher = SemesterPublisher()
    async with publisher.clients() as (runtime, rest, mcp):
        response = await rest.get("/courses/99999")
        assert response.status_code == 404
        assert response.json() == {"detail": "Semester is not published."}
        result = await mcp.call_tool("search_courses", {"semester": "99999"}, raise_on_error=False)
        assert result.is_error
        assert "Semester is not published" in result.content[0].text
        assert "/courses/semesters/99999.json" not in runtime.datasets.states
        publisher.errors["/courses/semesters/11420.json"] = 503
        assert (await rest.get("/courses/11420")).status_code == 503
        result = await mcp.call_tool("search_courses", {"semester": "11420"}, raise_on_error=False)
        assert result.is_error
        assert not publisher.calls["/courses/latest.json"]
        assert (await rest.get("/courses/11510")).status_code == 200


async def test_catalog_failure_does_not_block_latest_or_claim_unknown_is_missing():
    publisher = SemesterPublisher()
    async with publisher.clients() as (_, rest, _):
        publisher.errors["/courses/sources.json"] = 503
        assert (await rest.get("/courses/11420")).status_code == 503
        assert (await rest.get("/courses")).status_code == 200
    publisher.errors.clear()
    async with publisher.clients() as (runtime, rest, _):
        assert (await rest.get("/courses/11420")).status_code == 200
        publisher.errors["/file_details.json"] = 503
        publisher.clock.advance()
        assert (await rest.get("/courses/99999")).status_code == 503
        assert runtime.courses.catalog_state.freshness == Freshness.UNVERIFIED
        assert (await rest.get("/courses/11420")).status_code == 200


async def test_cross_semester_concurrency_coalesces_only_same_path_and_keeps_versions():
    publisher = SemesterPublisher()
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(request):
        if request.url.path == "/courses/semesters/11420.json":
            entered.set()
            await release.wait()
        return await publisher(request)

    runtime = Runtime.create(NTHUDataManager(clock=publisher.clock))
    async with runtime.datasets.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(runtime)), base_url="http://test"
        ) as rest:
            pending = [asyncio.create_task(rest.get("/courses/11420")) for _ in range(20)]
            await asyncio.wait_for(entered.wait(), 2)
            other = await asyncio.wait_for(rest.get("/courses/11510"), 2)
            assert other.json()[0]["id"] == "11510NEW"
            release.set()
            responses = await asyncio.gather(*pending)
            assert all(r.json()[0]["id"] == "11420OLD" for r in responses)
            assert all(
                r.headers["X-Data-Commit-Hash"] == "a/courses/semesters/11420.json"
                for r in responses
            )
            assert publisher.calls["/courses/semesters/11420.json"] == 1


async def test_failed_refresh_retains_only_same_semester_and_recovers_after_ttl():
    publisher = SemesterPublisher()
    async with publisher.clients() as (runtime, rest, _):
        before = await rest.get("/courses/11420")
        publisher.version = "b"
        publisher.documents["/courses/semesters/11420.json"] = [course_payload()]
        publisher.clock.advance()
        stale = await rest.get("/courses/11420")
        assert stale.json() == before.json()
        assert stale.headers["X-Data-Commit-Hash"] == before.headers["X-Data-Commit-Hash"]
        state = runtime.datasets.states["/courses/semesters/11420.json"]
        assert state.freshness == Freshness.STALE
        calls = publisher.calls.copy()
        assert (await rest.get("/courses/11420")).status_code == 200
        assert publisher.calls == calls
        publisher.documents["/courses/semesters/11420.json"] = []
        publisher.clock.advance()
        empty = await rest.get("/courses/11420")
        assert empty.json() == []
        assert empty.headers["X-Total-Count"] == "0"
        assert state.freshness == Freshness.CURRENT
    assert all(not state.usable for state in runtime.datasets.states.values())


async def test_filters_apply_to_selected_semester_and_teacher_union():
    publisher = SemesterPublisher()
    async with publisher.clients() as (_, rest, mcp):
        response = await rest.get("/courses/11420", params={"lecturers.label": r"\[AI\]"})
        assert len(response.json()) == 1
        assert (await rest.get("/courses/11420?type=microcredits")).json() == response.json()
        assert (await rest.get("/courses/11420?credits=3")).json() == []
        for teacher in ["Old [AI]", "[AI]"]:
            result = await mcp.call_tool(
                "search_courses", {"semester": "11420", "teacher": teacher}
            )
            assert result.data["courses"] == response.json()
        for teacher in ["老師", "Teacher"]:
            result = await mcp.call_tool(
                "search_courses", {"semester": "11510", "teacher": teacher}
            )
            assert result.data["count"] == 1
        result = await mcp.call_tool("search_courses", {"semester": "11420", "teacher": "missing"})
        assert result.data == {"count": 0, "courses": []}


async def test_catalog_refresh_discovers_new_semester_and_rejects_invalid_replacement():
    publisher = SemesterPublisher()
    async with publisher.clients() as (runtime, rest, _):
        initial = await rest.get("/courses/semesters")
        assert (await rest.get("/courses/11610")).status_code == 404
        publisher.catalog.append("11610")
        publisher.documents["/courses/semesters/11610.json"] = [
            course_payload(id="11610NEW", semester_code="11610")
        ]
        publisher.version = "b"
        publisher.clock.advance()
        assert (await rest.get("/courses/11610")).json()[0]["id"] == "11610NEW"
        publisher.catalog.append("11610")
        publisher.version = "c"
        publisher.clock.advance()
        catalog = await rest.get("/courses/semesters")
        assert catalog.json() == ["11610"] + initial.json()
        assert runtime.courses.catalog_state.freshness == Freshness.STALE
        assert (await rest.get("/courses/11710")).status_code == 503


async def test_cancellation_releases_semester_lock_and_allows_retry():
    publisher = SemesterPublisher()
    entered = asyncio.Event()
    block = True

    async def handler(request):
        if request.url.path == "/courses/semesters/11420.json" and block:
            entered.set()
            await asyncio.Event().wait()
        return await publisher(request)

    runtime = Runtime.create(NTHUDataManager(clock=publisher.clock))
    async with runtime.datasets.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        task = asyncio.create_task(runtime.courses.get_snapshot("11420"))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        state = runtime.datasets.states["/courses/semesters/11420.json"]
        assert not state.lock.locked()
        block = False
        snapshot = await runtime.courses.get_snapshot("11420")
        assert snapshot.data[0].id == "11420OLD"


async def test_lazy_unavailable_semester_is_reported_by_readiness_without_refresh():
    publisher = SemesterPublisher()
    async with publisher.clients() as (_, rest, _):
        publisher.errors["/courses/semesters/11420.json"] = 503
        assert (await rest.get("/courses/11420")).status_code == 503
        calls = publisher.calls.copy()
        response = await rest.get("/ping")
        assert response.status_code == 503
        assert response.json()["datasets"]["/courses/semesters/11420.json"]["usable"] is False
        assert publisher.calls == calls
