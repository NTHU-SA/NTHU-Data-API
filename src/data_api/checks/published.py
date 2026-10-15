"""Opt-in publisher checks: python -m data_api.checks.published."""

import argparse
import asyncio
import json
import math
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from data_api.api.api import create_app
from data_api.api.schemas.buses import BusCanonicalDetailedSchedule, BusCanonicalSchedule
from data_api.api.schemas.courses import CourseData
from data_api.checks.common import CheckFailure, fetch_json, report, validation_reason
from data_api.checks.smoke import ENDPOINTS, EndpointCheck, check_endpoints
from data_api.core.config import PREFETCH_ENDPOINTS
from data_api.data.nthudata import (
    FetchFailure,
    JsonData,
    ManifestEntry,
    NTHUDataManager,
    parse_manifest,
)
from data_api.domain.buses.services import PreparedBusData
from data_api.domain.courses.services import prepare_catalog, prepare_courses
from data_api.runtime import Runtime

MANIFEST_PATH = "/file_details.json"


def _check_serialization(path: str, candidate: Any) -> None:
    try:
        if path == "/courses/latest.json" or path.startswith("/courses/semesters/"):
            adapter = TypeAdapter(list[CourseData])
            parsed = adapter.validate_python(candidate, from_attributes=True)
            adapter.dump_json(parsed, warnings="error")
        elif isinstance(candidate, PreparedBusData):
            for model, store in [
                (BusCanonicalSchedule, candidate.raw_schedule_data),
                (BusCanonicalDetailedSchedule, candidate.detailed_schedule_data),
            ]:
                adapter = TypeAdapter(list[model])
                for rows in store.values():
                    adapter.dump_json(adapter.validate_python(rows), warnings="error")
        else:
            TypeAdapter(JsonData).dump_json(candidate, warnings="error")
    except (ValidationError, ValueError) as exc:
        reason = validation_reason(exc) if isinstance(exc, ValidationError) else type(exc).__name__
        raise CheckFailure(path, "serialization", reason) from exc


async def _check_download(
    client: httpx.AsyncClient, data_url: str, path: str, checksum: str | None, runtime: Runtime
) -> bytes:
    payload, response = await fetch_json(client, f"{data_url}{path}", path, checksum)
    try:
        if path.startswith("/courses/semesters/"):
            semester = path.rsplit("/", 1)[1].removesuffix(".json")
            candidate = prepare_courses(payload, semester)
        else:
            candidate = runtime.datasets.state_for(path).prepare(payload)
    except ValidationError as exc:
        raise CheckFailure(path, "candidate", validation_reason(exc)) from exc
    except FetchFailure as exc:
        raise CheckFailure(path, "candidate", exc.category) from exc
    except ValueError as exc:
        raise CheckFailure(path, "transformation", type(exc).__name__) from exc
    _check_serialization(path, candidate)
    return response.content


async def _check_local_responses(
    documents: dict[str, bytes], entries: dict[str, ManifestEntry], runtime: Runtime
) -> list[CheckFailure]:
    def serve_downloaded(request: httpx.Request) -> httpx.Response:
        content = documents.get(request.url.path)
        if content is None:
            return httpx.Response(404)
        return httpx.Response(200, content=content, headers={"content-type": "application/json"})

    # Serialization uses exactly the checked bytes, never a second publisher download or live API.
    failures = []
    nthudata = runtime.datasets
    async with nthudata.lifespan(
        httpx.AsyncClient(transport=httpx.MockTransport(serve_downloaded))
    ):
        results = await nthudata.prefetch(PREFETCH_ENDPOINTS)
        for endpoint, usable in results.items():
            if not usable:
                state = nthudata.state_for(endpoint)
                failures.append(
                    CheckFailure(
                        f"/{endpoint}",
                        "installation",
                        state.last_error.category if state.last_error else "unavailable",
                    )
                )
        if failures:
            return failures
        await runtime.courses.get_snapshot()
        await runtime.buses.update_data()
        expected_versions = {
            check.path: entries[check.dataset].active_version for check in ENDPOINTS
        }
        expected_versions["/calendars"], _ = await runtime.calendars.get_all_calendars()
        checks = list(ENDPOINTS)
        for semester in prepare_catalog(json.loads(documents["/courses/sources.json"])):
            path = f"/courses/{semester}"
            dataset = f"/courses/semesters/{semester}.json"
            checks.append(EndpointCheck(path, TypeAdapter(list[CourseData]), dataset, counted=True))
            expected_versions[path] = entries[dataset].active_version
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(runtime)),
            base_url="http://contract.test",
        ) as local:
            failures = await check_endpoints(
                local, "http://contract.test", expected_versions, checks=checks
            )
    return [
        CheckFailure(failure.target, f"serialization/{failure.stage}", failure.reason)
        for failure in failures
    ]


async def check_published(client: httpx.AsyncClient, data_url: str) -> list[CheckFailure]:
    data_url = data_url.rstrip("/")
    try:
        manifest, manifest_response = await fetch_json(
            client, f"{data_url}{MANIFEST_PATH}", MANIFEST_PATH
        )
        try:
            entries = parse_manifest(manifest)
        except FetchFailure as exc:
            raise CheckFailure(MANIFEST_PATH, "manifest", exc.category) from exc
    except CheckFailure as exc:
        return [exc]

    failures = []
    runtime = Runtime.create(NTHUDataManager(base_url=data_url))
    documents = {MANIFEST_PATH: manifest_response.content}
    for endpoint in PREFETCH_ENDPOINTS:
        path = f"/{endpoint}"
        try:
            if path not in entries:
                raise CheckFailure(path, "manifest", "required dataset is missing")
            documents[path] = await _check_download(
                client, data_url, path, entries[path].sha256, runtime
            )
        except CheckFailure as exc:
            failures.append(exc)
    if failures:
        return failures
    semesters = prepare_catalog(json.loads(documents["/courses/sources.json"]))
    for semester in semesters:
        path = f"/courses/semesters/{semester}.json"
        try:
            if path not in entries:
                raise CheckFailure(path, "manifest", "published semester dataset is missing")
            documents[path] = await _check_download(
                client, data_url, path, entries[path].sha256, runtime
            )
        except CheckFailure as exc:
            failures.append(exc)
    if failures:
        return failures
    return await _check_local_responses(documents, entries, runtime)


async def run(data_url: str, timeout: float) -> int:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        return report(await check_published(client, data_url), "published-data")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-url", default="https://data.nthusa.tw")
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    return asyncio.run(run(args.data_url, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
