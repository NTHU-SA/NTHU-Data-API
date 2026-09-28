"""Deterministic lifecycle tests: no network access or wall-clock sleeps."""

import asyncio
import hashlib
import socket
from dataclasses import replace

import httpx
import pytest
from pydantic import TypeAdapter

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.nthudata import FetchFailure, Freshness, NTHUDataManager
from data_api.domain.buses.services import BusesService
from data_api.domain.courses.services import CoursesService


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds=301):
        self.now += seconds


class Publisher:
    def __init__(self, payload=None, endpoint="test.json"):
        self.endpoint = endpoint
        self.payload = [] if payload is None else payload
        self.version = "a"
        self.manifest_override = None
        self.manifest_error = None
        self.data_error = None
        self.calls = []
        self.sha256 = None

    def manifest(self):
        entry = {"name": self.endpoint, "last_commit": self.version}
        if self.sha256:
            entry["sha256"] = self.sha256
        return {"file_details": {"/": [entry]}}

    async def __call__(self, request):
        self.calls.append(request.url.path)
        manifest = request.url.path == "/file_details.json"
        failure = self.manifest_error if manifest else self.data_error
        if isinstance(failure, Exception):
            raise failure
        if isinstance(failure, int):
            return httpx.Response(failure)
        if manifest:
            payload = (
                self.manifest_override if self.manifest_override is not None else self.manifest()
            )
        else:
            payload = self.payload
        if isinstance(payload, bytes):
            return httpx.Response(200, content=payload)
        return httpx.Response(200, json=payload)

    def client(self):
        return httpx.AsyncClient(transport=httpx.MockTransport(self))


async def test_prefetch_starts_datasets_concurrently_and_reports_failures(monkeypatch):
    manager = NTHUDataManager()
    started = set()
    all_started = asyncio.Event()
    endpoints = ["first.json", "unavailable.json", "last.json"]

    async def get(endpoint):
        started.add(endpoint)
        if started == set(endpoints):
            all_started.set()
        await all_started.wait()
        if endpoint == "unavailable.json":
            raise DataNotAvailableException("Unavailable")
        return "version", []

    monkeypatch.setattr(manager, "get", get)
    async with asyncio.timeout(5):
        result = await manager.prefetch(endpoints)
    assert result == {"first.json": True, "unavailable.json": False, "last.json": True}
    assert await manager.prefetch([]) == {}


@pytest.mark.parametrize("initial,new", [([1], [2]), ([1], []), ({"a": 1}, {})])
async def test_successful_replacement_including_empty(initial, new):
    clock, publisher = Clock(), Publisher(initial)
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        assert await manager.get("test.json") == ("a", initial)
        old = manager.state_for("test.json").snapshot
        publisher.version, publisher.payload = "b", new
        clock.advance()
        assert await manager.get("/test.json") == ("b", new)
        state = manager.state_for("test.json")
        assert state.snapshot is not old
        assert state.freshness == Freshness.CURRENT
        assert state.last_refresh_success_at == state.snapshot.loaded_at


@pytest.mark.parametrize(
    "failure,category",
    [
        (httpx.ReadTimeout("secret URL"), "timeout"),
        (httpx.ConnectError("secret URL"), "connection"),
        (httpx.RemoteProtocolError("protocol"), "request"),
        (404, "http_status"),
        (500, "http_status"),
        (503, "http_status"),
        (b"not json", "invalid_json"),
        (b"null", "payload_type"),
        (b"42", "payload_type"),
    ],
)
@pytest.mark.parametrize("initial_loaded", [True, False])
async def test_fetch_failures_preserve_last_known_good(failure, category, initial_loaded):
    clock, publisher = Clock(), Publisher([1])
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        state = manager.state_for("test.json")
        if initial_loaded:
            await manager.get("test.json")
        old = state.snapshot
        publisher.version = "b"
        if isinstance(failure, bytes):
            publisher.payload = failure
        else:
            publisher.data_error = failure
        clock.advance()
        if initial_loaded:
            assert await manager.get("test.json") == ("a", [1])
        else:
            with pytest.raises(DataNotAvailableException, match="temporarily unavailable"):
                await manager.get("test.json")
        assert state.snapshot is old
        assert state.last_error.category == category
        assert state.freshness == (Freshness.STALE if initial_loaded else Freshness.UNAVAILABLE)
        calls = len(publisher.calls)
        if initial_loaded:
            await manager.get("test.json")
        else:
            with pytest.raises(DataNotAvailableException):
                await manager.get("test.json")
        assert len(publisher.calls) == calls
        assert "secret" not in str(state.last_error)


async def test_dns_category_preserves_cause():
    publisher = Publisher()
    error = httpx.ConnectError("connection")
    error.__cause__ = socket.gaierror("DNS")
    publisher.data_error = error
    manager = NTHUDataManager()
    async with manager.lifespan(publisher.client()):
        with pytest.raises(DataNotAvailableException):
            await manager.get("test.json")
        assert manager.state_for("test.json").last_error.category == "dns"


async def test_ttl_and_version_matching():
    clock, publisher = Clock(), Publisher([1])
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        await manager.get("test.json")
        state = manager.state_for("test.json")
        old = state.snapshot
        clock.advance(299)
        await manager.get("test.json")
        assert len(publisher.calls) == 2
        clock.advance(1)
        await manager.get("test.json")
        assert publisher.calls == ["/file_details.json", "/test.json", "/file_details.json"]
        assert state.snapshot is old
        assert state.freshness == Freshness.CURRENT
        assert state.last_refresh_success_at == old.loaded_at


@pytest.mark.parametrize("current,expected", [("a", None), (None, None), (None, "a"), ("a", "b")])
async def test_unknown_versions_are_not_a_match(current, expected):
    clock, publisher = Clock(), Publisher([1])
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        await manager.get("test.json")
        state = manager.state_for("test.json")
        state.snapshot = replace(state.snapshot, version=current)
        publisher.version, publisher.payload = expected, [2]
        clock.advance()
        version, data = await manager.get("test.json")
        if expected is None:
            assert (version, data) == (current, [1])
            assert state.freshness == Freshness.UNVERIFIED
            assert publisher.calls.count("/test.json") == 1
        else:
            assert (version, data) == (expected, [2])
            assert publisher.calls.count("/test.json") == 2


@pytest.mark.parametrize(
    "manifest,category",
    [
        ([], "manifest_parsing"),
        ({}, "manifest_parsing"),
        ({"file_details": []}, "manifest_parsing"),
        ({"file_details": {"/": [42]}}, "manifest_parsing"),
        ({"file_details": {"/": [{"name": "test.json", "last_commit": 42}]}}, "manifest_parsing"),
        ({"file_details": {"/": [{"name": "test.json", "sha256": "bad"}]}}, "manifest_parsing"),
        ({"file_details": {"/": []}}, "version_unknown"),
        ({"file_details": {"/": [{"name": "test.json"}]}}, "version_unknown"),
        (b"bad json", "manifest_parsing"),
    ],
)
async def test_manifest_contract_failures(manifest, category):
    clock, publisher = Clock(), Publisher([1])
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        await manager.get("test.json")
        state = manager.state_for("test.json")
        old = state.snapshot
        clock.advance()
        publisher.manifest_override = manifest
        assert await manager.get("test.json") == ("a", [1])
        assert state.snapshot is old
        assert state.last_error.category == category
        assert state.freshness == Freshness.UNVERIFIED
        assert publisher.calls.count("/test.json") == 1


async def test_manifest_extra_fields_optional_metadata_and_nested_paths():
    publisher = Publisher([1], endpoint="libraries/rss.json")
    publisher.manifest_override = {
        "extra": "ignored",
        "file_details": {
            "libraries": [{"name": "rss.json", "version": "b", "extra": "ignored"}],
        },
    }
    manager = NTHUDataManager(base_url="https://example.com/")
    # Generic payload for a nested endpoint, independent of the RSS schema.
    manager.register("/libraries/rss.json", lambda raw: raw)
    async with manager.lifespan(publisher.client()):
        assert await manager.get("libraries/rss.json") == ("b", [1])
        assert publisher.calls == ["/file_details.json", "/libraries/rss.json"]
        assert manager.state_for("libraries/rss.json").snapshot.published_at is None


@pytest.mark.parametrize("loaded", [False, True])
async def test_manifest_outage_never_claims_freshness(loaded):
    clock, publisher = Clock(), Publisher([1])
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        if loaded:
            await manager.get("test.json")
        publisher.manifest_error = 503
        clock.advance()
        assert await manager.get("test.json") == ("a" if loaded else None, [1])
        state = manager.state_for("test.json")
        assert state.freshness == Freshness.UNVERIFIED
        assert state.last_error.status_code == 503
        count = len(publisher.calls)
        await manager.get("test.json")
        assert len(publisher.calls) == count


@pytest.mark.parametrize("stage", ["validation", "transformation", "programming"])
async def test_candidate_failure_is_atomic(stage):
    clock, publisher = Clock(), Publisher([1])
    manager = NTHUDataManager(clock=clock)

    def prepare(raw):
        if raw == [2]:
            if stage == "validation":
                TypeAdapter(list[str]).validate_python(raw)
            elif stage == "transformation":
                raise ValueError("Failed model conversion")
            else:
                raise RuntimeError("Programming error must not be swallowed")
        return {"index": {str(value): value for value in raw}}

    state = manager.register("test.json", prepare)
    async with manager.lifespan(publisher.client()):
        await manager.get("test.json")
        old = state.snapshot
        publisher.version, publisher.payload = "b", [2]
        clock.advance()
        if stage == "programming":
            with pytest.raises(RuntimeError, match="Programming"):
                await manager.get("test.json")
        else:
            assert await manager.get("test.json") == ("a", [1])
            assert state.last_error.category == stage
        assert state.snapshot is old
        assert state.snapshot.data == {"index": {"1": 1}}


@pytest.mark.parametrize("fail", [False, True])
async def test_twenty_concurrent_callers_single_refresh(fail):
    clock, publisher = Clock(), Publisher([1])
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(request):
        if request.url.path == "/test.json" and publisher.version == "b":
            entered.set()
            await release.wait()
        return await publisher(request)

    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        await manager.get("test.json")
        old = manager.state_for("test.json").snapshot
        publisher.version, publisher.payload = "b", [2]
        if fail:
            publisher.data_error = 503
        clock.advance()
        tasks = [asyncio.create_task(manager.get("test.json")) for _ in range(20)]
        await asyncio.wait_for(entered.wait(), 2)
        assert manager.state_for("test.json").snapshot is old
        release.set()
        results = await asyncio.gather(*tasks)
        assert all(result == (("a", [1]) if fail else ("b", [2])) for result in results)
        assert publisher.calls.count("/test.json") == 2
        assert publisher.calls.count("/file_details.json") == 2


async def test_unrelated_dataset_downloads_do_not_block():
    entered, release = asyncio.Event(), asyncio.Event()
    publisher = Publisher([1])
    publisher.manifest_override = {
        "file_details": {
            "/": [
                {"name": "slow.json", "last_commit": "a"},
                {"name": "fast.json", "last_commit": "a"},
            ]
        }
    }

    async def handler(request):
        if request.url.path == "/slow.json":
            entered.set()
            await release.wait()
        return await publisher(request)

    manager = NTHUDataManager()
    async with manager.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        slow = asyncio.create_task(manager.get("slow.json"))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            assert await asyncio.wait_for(manager.get("fast.json"), 2) == ("a", [1])
        finally:
            release.set()
            await slow
        assert publisher.calls.count("/file_details.json") == 1


async def test_checksum_prevents_mislabeled_snapshot_during_publication():
    clock, publisher = Clock(), Publisher([1])
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        await manager.get("test.json")
        publisher.version = "b"
        publisher.sha256 = hashlib.sha256(b"[2]").hexdigest()
        clock.advance()
        assert await manager.get("test.json") == ("a", [1])
        assert manager.state_for("test.json").last_error.category == "checksum"
        publisher.payload = b"[2]"
        clock.advance()
        assert await manager.get("test.json") == ("b", [2])


async def test_course_validation_and_conversion_before_swap(monkeypatch):
    clock, publisher = Clock(), Publisher([{"id": "A", "language": "中"}], "courses.json")
    manager = NTHUDataManager(clock=clock)
    service = CoursesService(manager)
    async with manager.lifespan(publisher.client()):
        await service.update_data()
        old = service.state.snapshot
        for payload in [[], [{"id": "B", "language": "中"}]]:
            publisher.version += "b"
            publisher.payload = payload
            clock.advance()
            await service.update_data()
            assert [c.id for c in service.course_data] == [r["id"] for r in payload]
        old = service.state.snapshot
        publisher.version, publisher.payload = "invalid", [{"id": None}]
        clock.advance()
        await service.update_data()
        assert service.state.snapshot is old
        assert service.state.last_error.category == "validation"

        from data_api.domain.courses.models import CourseData

        def fail(raw):
            raise ValueError("conversion failed")

        monkeypatch.setattr(CourseData, "from_dict", fail)
        publisher.payload = [{"id": "C"}]
        clock.advance()
        await service.update_data()
        assert service.state.snapshot is old
        assert service.state.last_error.category == "transformation"


async def test_bus_indexes_are_built_before_swap(monkeypatch):
    clock = Clock()
    payload = {
        "weekdayBusScheduleTowardTSMCBuilding": [
            {"time": "8:00", "description": "", "line": "red", "dep_stop": "gate"}
        ]
    }
    publisher = Publisher(payload, "buses.json")
    manager = NTHUDataManager(clock=clock)
    service = BusesService(manager)
    async with manager.lifespan(publisher.client()):
        await service.update_data()
        old = service.state.snapshot
        old_registry = service.stops_schedule_registry

        def fail(self):
            raise ValueError("index construction failed")

        with monkeypatch.context() as patch:
            patch.setattr(BusesService, "_derive_combined_views", fail)
            publisher.version = "b"
            clock.advance()
            await service.update_data()
            assert service.state.snapshot is old
            assert service.stops_schedule_registry is old_registry
        publisher.payload = {}
        clock.advance()
        await service.update_data()
        assert service.state.snapshot.version == "b"
        assert not any(service.raw_schedule_data.values())


async def test_bus_candidate_must_also_satisfy_response_schema():
    publisher = Publisher(
        {"weekdayBusScheduleTowardTSMCBuilding": [{"time": "8:00", "description": ""}]},
        "buses.json",
    )
    manager = NTHUDataManager()
    service = BusesService(manager)
    async with manager.lifespan(publisher.client()):
        with pytest.raises(DataNotAvailableException):
            await service.update_data()
        assert service.state.last_error.category == "validation"
        assert not service.state.usable


@pytest.mark.parametrize("fail_startup", [False, True])
async def test_client_lifecycle_and_disposable_state(fail_startup):
    publisher = Publisher([1])
    manager = NTHUDataManager()
    client = publisher.client()
    assert manager.fetcher.client is None
    try:
        async with manager.lifespan(client):
            await manager.get("test.json")
            assert manager.fetcher.client is client
            if fail_startup:
                raise RuntimeError("startup")
    except RuntimeError:
        assert fail_startup
    assert client.is_closed
    assert manager.fetcher.client is None
    assert not manager.state_for("test.json").usable
    publisher.data_error = 503
    async with manager.lifespan(publisher.client()):
        with pytest.raises(DataNotAvailableException):
            await manager.get("test.json")


async def test_cancelled_refresh_can_retry():
    publisher = Publisher([1])
    entered = asyncio.Event()
    block = True

    async def handler(request):
        if request.url.path == "/test.json" and block:
            entered.set()
            await asyncio.Event().wait()
        return await publisher(request)

    manager = NTHUDataManager()
    async with manager.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        task = asyncio.create_task(manager.get("test.json"))
        await asyncio.wait_for(entered.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        block = False
        assert await manager.get("test.json") == ("a", [1])


async def test_shared_manifest_does_not_extend_freshness_for_later_readers():
    clock, publisher = Clock(), Publisher([1])
    publisher.manifest_override = {
        "file_details": {
            "/": [
                {"name": "first.json", "last_commit": "a"},
                {"name": "later.json", "last_commit": "a"},
            ]
        }
    }
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        await manager.get("first.json")
        clock.advance(299)
        await manager.get("later.json")
        assert publisher.calls.count("/file_details.json") == 1
        clock.advance(1)
        await manager.get("later.json")
        assert publisher.calls.count("/file_details.json") == 2
        assert publisher.calls.count("/later.json") == 1


@pytest.mark.parametrize("payload", [[], [{"id": "B", "language": "invalid"}], [42], {"id": "B"}])
async def test_initial_course_schema_validation(payload):
    publisher = Publisher(payload, "courses.json")
    manager = NTHUDataManager()
    service = CoursesService(manager)
    async with manager.lifespan(publisher.client()):
        if payload == []:
            await service.update_data()
            assert service.course_data == []
            assert service.state.usable
        else:
            with pytest.raises(DataNotAvailableException):
                await service.update_data()
            assert not service.state.usable
            assert service.state.last_error.category in {"validation", "payload_type"}


@pytest.mark.parametrize(
    "endpoint,valid,invalid",
    [
        (
            "announcements.json",
            [
                {
                    "title": "News",
                    "department": "Office",
                    "language": "en",
                    "link": "https://example.com",
                    "articles": [],
                }
            ],
            [{"title": "News", "articles": [42]}],
        ),
        (
            "announcements_list.json",
            [
                {
                    "title": "News",
                    "department": "Office",
                    "language": "en",
                    "link": "https://example.com",
                }
            ],
            [{"title": "News"}],
        ),
        (
            "dining.json",
            [
                {
                    "building": "Hall",
                    "restaurants": [
                        {
                            "name": "Shop",
                            "area": "Hall",
                            "image": None,
                            "note": "",
                            "phone": "",
                            "schedule": {},
                        }
                    ],
                }
            ],
            [{"building": "Hall", "restaurants": [42]}],
        ),
        (
            "directory.json",
            [{"index": "01", "name": "Office", "details": {"people": []}}],
            [{"index": "01", "name": "Office", "details": {"people": [42]}}],
        ),
        (
            "maps.json",
            {"main": {"gate": {"latitude": "24", "longitude": "120"}}},
            {"main": {"gate": {"latitude": 24}}},
        ),
        (
            "newsletters.json",
            [{"name": "News", "link": "https://example.com", "details": {}, "articles": []}],
            [{"name": "News", "link": "https://example.com", "details": {}, "articles": [42]}],
        ),
        ("libraries/rss.json", {"news": []}, {"news": [42]}),
        (
            "libraries/calendars.json",
            [
                {
                    "id": "main",
                    "name": None,
                    "description": None,
                    "timezone": "Asia/Taipei",
                    "url": "https://example.com",
                    "events": [],
                }
            ],
            [
                {
                    "id": "main",
                    "name": None,
                    "description": None,
                    "timezone": "Asia/Taipei",
                    "url": "https://example.com",
                    "events": [
                        {
                            "id": "x",
                            "title": "Hours",
                            "description": None,
                            "all_day": True,
                            "start": "invalid-date",
                            "end": "2026-09-29",
                        }
                    ],
                }
            ],
        ),
    ],
)
async def test_dataset_schemas_validate_nested_records_before_install(endpoint, valid, invalid):
    clock, publisher = Clock(), Publisher(valid, endpoint)
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        await manager.get(endpoint)
        state = manager.state_for(endpoint)
        old = state.snapshot
        publisher.version, publisher.payload = "b", invalid
        clock.advance()
        assert await manager.get(endpoint) == ("a", valid)
        assert state.snapshot is old
        assert state.last_error.category == "validation"
        publisher.payload = {} if isinstance(valid, dict) else []
        clock.advance()
        assert await manager.get(endpoint) == ("b", publisher.payload)


async def test_concurrent_cold_failure_is_one_attempt_then_recover():
    clock, publisher = Clock(), Publisher([1])
    publisher.data_error = 503
    manager = NTHUDataManager(clock=clock)
    async with manager.lifespan(publisher.client()):
        results = await asyncio.gather(
            *(manager.get("test.json") for _ in range(20)), return_exceptions=True
        )
        assert all(isinstance(result, DataNotAvailableException) for result in results)
        assert publisher.calls == ["/file_details.json", "/test.json"]
        publisher.data_error = None
        clock.advance()
        assert await manager.get("test.json") == ("a", [1])


async def test_instances_are_independent():
    clock_a, clock_b, publisher = Clock(), Clock(), Publisher([1])
    first, second = NTHUDataManager(clock=clock_a), NTHUDataManager(clock=clock_b)
    async with first.lifespan(publisher.client()), second.lifespan(publisher.client()):
        await first.get("test.json")
        await second.get("test.json")
        publisher.version, publisher.payload = "b", [2]
        clock_a.advance()
        assert await first.get("test.json") == ("b", [2])
        assert await second.get("test.json") == ("a", [1])
        clock_b.advance()
        assert await second.get("test.json") == ("b", [2])
        assert first.state_for("test.json").lock is not second.state_for("test.json").lock


async def test_duplicate_manifest_paths_are_malformed():
    publisher = Publisher()
    publisher.manifest_override = {
        "file_details": {
            "/": [
                {"name": "test.json", "last_commit": "a"},
                {"name": "test.json", "last_commit": "b"},
            ]
        }
    }
    manager = NTHUDataManager()
    async with manager.lifespan(publisher.client()):
        assert await manager.get("test.json") == (None, [])
        assert manager.state_for("test.json").last_error.category == "manifest_parsing"


def test_runtime_settings_are_configurable_and_positive(monkeypatch):
    from pydantic import ValidationError

    from data_api.core.settings import Settings

    monkeypatch.setenv("FILE_DETAILS_CACHE_EXPIRY", "120")
    monkeypatch.setenv("DATA_HTTP_TIMEOUT", "5")
    settings = Settings(_env_file=None)
    assert settings.file_details_cache_expiry == 120
    assert settings.data_http_timeout == 5
    monkeypatch.setenv("FILE_DETAILS_CACHE_EXPIRY", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
