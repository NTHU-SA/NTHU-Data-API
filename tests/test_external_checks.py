"""All external-check tests use mock transports, never live services."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from data_api.api.schemas.ping import DatasetHealth, PingResponse
from data_api.checks.common import CheckFailure, fetch_json, report
from data_api.checks.published import check_published
from data_api.checks.smoke import ENDPOINTS, check_endpoints, check_smoke
from data_api.core.config import PREFETCH_ENDPOINTS
from data_api.data.nthudata import Freshness


@pytest.fixture
def publication():
    rss = json.loads(
        (Path(__file__).parent / "fixtures" / "library_rss_published_urls.json").read_text(
            encoding="utf-8"
        )
    )
    payloads = {f"/{path}": [] for path in PREFETCH_ENDPOINTS}
    payloads.update(
        {
            "/buses.json": {},
            "/maps.json": {},
            "/courses.json": [{"id": "11510TEST100000", "chinese_title": "Test", "language": "中"}],
            "/libraries/rss.json": rss,
        }
    )
    documents = {path: json.dumps(payload).encode() for path, payload in payloads.items()}
    manifest = {"file_details": {"/": [], "libraries": []}}
    for path, content in documents.items():
        section, _, name = path.lstrip("/").rpartition("/")
        manifest["file_details"][section or "/"].append(
            {"name": name, "last_commit": "fixture", "sha256": hashlib.sha256(content).hexdigest()}
        )
    return documents, manifest


def published_client(documents, manifest, overrides=None):
    def serve(request):
        if request.url.path in (overrides or {}):
            result = overrides[request.url.path]
            if isinstance(result, Exception):
                raise result
            return result
        if request.url.path == "/file_details.json":
            return httpx.Response(200, json=manifest)
        if request.url.path in documents:
            return httpx.Response(
                200,
                content=documents[request.url.path],
                headers={"content-type": "application/json"},
            )
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(serve))


async def test_complete_publication_accepts_url_regressions_and_serializes(publication):
    documents, manifest = publication
    original = deepcopy(documents)
    async with published_client(documents, manifest) as client:
        assert await check_published(client, "https://publisher.test/") == []
    assert documents == original


async def test_legacy_manifest_and_empty_datasets_are_accepted(publication):
    documents, manifest = publication
    for entries in manifest["file_details"].values():
        for entry in entries:
            entry.pop("last_commit")
            entry.pop("sha256")
    documents["/courses.json"] = b"[]"
    documents["/libraries/rss.json"] = json.dumps(
        {"news": [], "eresources": [], "exhibit": [], "branches": []}
    ).encode()
    async with published_client(documents, manifest) as client:
        assert await check_published(client, "https://publisher.test") == []


@pytest.mark.parametrize(
    "response,stage,reason",
    [
        (httpx.Response(404), "http", "status 404"),
        (
            httpx.Response(
                200, text="<html>not a dataset</html>", headers={"content-type": "text/html"}
            ),
            "content-type",
            "expected application/json",
        ),
        (
            httpx.Response(200, content=b"not json", headers={"content-type": "application/json"}),
            "checksum",
            "SHA-256 mismatch",
        ),
        (httpx.ReadTimeout("private URL"), "http", "timeout"),
        (httpx.ConnectError("private URL"), "http", "connection/request failure"),
    ],
)
async def test_delivery_failures_identify_dataset_and_stage(publication, response, stage, reason):
    documents, manifest = publication
    async with published_client(documents, manifest, {"/directory.json": response}) as client:
        failures = await check_published(client, "https://publisher.test")
    assert failures == [CheckFailure("/directory.json", stage, reason)]


@pytest.mark.parametrize(
    "path,payload,expected_stage",
    [
        ("/directory.json", [{"unexpected": "private payload"}], "candidate"),
        ("/courses.json", [{"id": ""}], "candidate"),
        ("/buses.json", {"unexpected": []}, "candidate"),
        (
            "/libraries/rss.json",
            {"news": [{"title": "Article", "description": "", "image": {"url": "https://"}}]},
            "candidate",
        ),
    ],
)
async def test_schema_drift_fails_full_candidate(publication, path, payload, expected_stage):
    documents, manifest = publication
    documents[path] = json.dumps(payload).encode()
    for entries in manifest["file_details"].values():
        for entry in entries:
            entry.pop("sha256")
    async with published_client(documents, manifest) as client:
        failures = await check_published(client, "https://publisher.test")
    assert len(failures) == 1
    assert failures[0].target == path
    assert failures[0].stage == expected_stage
    assert "private payload" not in str(failures[0])


async def test_missing_required_manifest_entry_is_not_silently_loaded(publication):
    documents, manifest = publication
    manifest["file_details"]["libraries"] = []
    async with published_client(documents, manifest) as client:
        failures = await check_published(client, "https://publisher.test")
    assert {failure.target for failure in failures} == {
        "/libraries/rss.json",
        "/libraries/calendars.json",
    }
    assert all(failure.stage == "manifest" for failure in failures)


async def test_duplicate_manifest_is_rejected(publication):
    documents, manifest = publication
    manifest["file_details"]["/"].append(manifest["file_details"]["/"][0])
    async with published_client(documents, manifest) as client:
        failures = await check_published(client, "https://publisher.test")
    assert failures == [CheckFailure("/file_details.json", "manifest", "manifest_parsing")]


@pytest.mark.parametrize(
    "content,stage",
    [
        (b"invalid", "json"),
        (b'"\xff"', "json"),
        (b"null", "json"),
    ],
)
async def test_json_failures_without_checksum(content, stage):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=content, headers={"content-type": "application/json; charset=utf-8"}
            )
        )
    ) as client:
        with pytest.raises(CheckFailure) as error:
            await fetch_json(client, "https://publisher.test/test.json", "/test.json")
    assert error.value.stage == stage


def healthy_readiness():
    return PingResponse(
        status="ok",
        ready=True,
        checked_at=datetime.now(timezone.utc),
        datasets={
            f"/{path}": DatasetHealth(usable=True, freshness=Freshness.CURRENT)
            for path in PREFETCH_ENDPOINTS
        },
    ).model_dump(mode="json")


def smoke_client(overrides=None):
    def serve(request):
        if request.url.path in (overrides or {}):
            return overrides[request.url.path]
        if request.url.path == "/ping":
            return httpx.Response(
                200, json=healthy_readiness(), headers={"Cache-Control": "no-store"}
            )
        return httpx.Response(
            200, json=[], headers={"X-Process-Time": "0.01", "X-Total-Count": "0"}
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(serve))


async def test_smoke_accepts_empty_feeds_and_unknown_versions():
    async with smoke_client() as client:
        assert await check_smoke(client, "https://api.test/") == []
    rss_paths = [check.path for check in ENDPOINTS if check.path.startswith("/libraries/rss/")]
    assert set(rss_paths) == {
        "/libraries/rss/news",
        "/libraries/rss/eresources",
        "/libraries/rss/exhibit",
        "/libraries/rss/branches",
    }


@pytest.mark.parametrize("version", [None, "wrong-version", "expected-version"])
async def test_published_serialization_checks_expected_version_header(version):
    headers = {"X-Process-Time": "0.01", "X-Total-Count": "0"}
    if version is not None:
        headers["X-Data-Commit-Hash"] = version
    expected = {check.path: None for check in ENDPOINTS}
    expected["/courses"] = "expected-version"
    async with smoke_client({"/courses": httpx.Response(200, json=[], headers=headers)}) as client:
        failures = await check_endpoints(client, "https://api.test", expected)
    if version == "expected-version":
        assert failures == []
    else:
        assert len(failures) == 1
        assert failures[0].target == "/courses"
        assert failures[0].stage == "headers"


@pytest.mark.parametrize(
    "path,response,stage",
    [
        ("/libraries/rss/news", httpx.Response(503), "http"),
        ("/libraries/rss/branches", httpx.Response(200, json={}), "response-schema"),
        ("/directory", httpx.Response(200, json=[{"unexpected": "private"}]), "response-schema"),
        ("/courses", httpx.Response(200, json=[], headers={"X-Process-Time": "0.01"}), "headers"),
        (
            "/courses",
            httpx.Response(200, json=[], headers={"X-Process-Time": "nan", "X-Total-Count": "0"}),
            "headers",
        ),
        (
            "/courses",
            httpx.Response(200, json=[], headers={"X-Process-Time": "0.01", "X-Total-Count": "53"}),
            "headers",
        ),
        ("/ping", httpx.Response(503), "http"),
        ("/ping", httpx.Response(200, json={}), "response-schema"),
        ("/ping", httpx.Response(200, json=healthy_readiness()), "headers"),
    ],
)
async def test_smoke_reports_endpoint_schema_headers_and_availability(path, response, stage):
    async with smoke_client({path: response}) as client:
        failures = await check_smoke(client, "https://api.test")
    assert len(failures) == 1
    assert failures[0].target == path
    assert failures[0].stage == stage


@pytest.mark.parametrize("missing,unusable", [(True, False), (False, True)])
async def test_smoke_rejects_false_readiness(missing, unusable):
    payload = healthy_readiness()
    if missing:
        del payload["datasets"]["/courses.json"]
    if unusable:
        payload["datasets"]["/courses.json"]["usable"] = False
    async with smoke_client(
        {"/ping": httpx.Response(200, json=payload, headers={"Cache-Control": "no-store"})}
    ) as client:
        failures = await check_smoke(client, "https://api.test")
    assert len(failures) == 1
    assert failures[0].stage == "readiness"


def test_external_report_exit_status_and_safe_diagnostic(capsys):
    assert report([], "published-data") == 0
    assert report([CheckFailure("/rss.json", "candidate", "validation")], "published-data") == 1
    output = capsys.readouterr().out
    assert "PASS published-data" in output
    assert "/rss.json: stage=candidate reason=validation" in output
