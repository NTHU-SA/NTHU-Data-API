"""Opt-in deployed API smoke checks: python -m data_api.checks.smoke."""

import argparse
import asyncio
import math
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from data_api.api.schemas.announcements import AnnouncementDetail, AnnouncementSource
from data_api.api.schemas.buses import BusCanonicalDetailedSchedule, BusInfo, BusStopsInfo
from data_api.api.schemas.calendars import Calendar
from data_api.api.schemas.courses import CourseData
from data_api.api.schemas.departments import Department
from data_api.api.schemas.dining import DiningBuilding
from data_api.api.schemas.libraries import LibraryRssItem, LibraryRssType
from data_api.api.schemas.locations import LocationDetail
from data_api.api.schemas.newsletters import NewsletterInfo, NewsletterSource
from data_api.api.schemas.ping import PingResponse
from data_api.checks.common import CheckFailure, fetch_json, report, validation_reason
from data_api.core.config import PREFETCH_ENDPOINTS


@dataclass(frozen=True)
class EndpointCheck:
    path: str
    adapter: TypeAdapter[Any]
    dataset: str
    counted: bool = False


ENDPOINTS = [
    EndpointCheck("/courses", TypeAdapter(list[CourseData]), "/courses.json", counted=True),
    EndpointCheck("/directory", TypeAdapter(list[Department]), "/directory.json"),
    EndpointCheck("/announcements", TypeAdapter(list[AnnouncementDetail]), "/announcements.json"),
    EndpointCheck(
        "/announcements/sources",
        TypeAdapter(list[AnnouncementSource]),
        "/announcements_list.json",
    ),
    EndpointCheck("/newsletters", TypeAdapter(list[NewsletterInfo]), "/newsletters.json"),
    EndpointCheck("/newsletters/sources", TypeAdapter(list[NewsletterSource]), "/newsletters.json"),
    EndpointCheck("/dining", TypeAdapter(list[DiningBuilding]), "/dining.json"),
    EndpointCheck("/locations", TypeAdapter(list[LocationDetail]), "/maps.json"),
    EndpointCheck("/buses/routes", TypeAdapter(list[BusInfo]), "/buses.json"),
    EndpointCheck("/buses/stops", TypeAdapter(list[BusStopsInfo]), "/buses.json"),
    EndpointCheck(
        "/buses/schedule?day=weekday&details=true&limit=5",
        TypeAdapter(list[BusCanonicalDetailedSchedule]),
        "/buses.json",
    ),
    EndpointCheck("/calendars", TypeAdapter(list[Calendar]), "/calendars.json"),
    *[
        EndpointCheck(
            f"/libraries/rss/{feed.value}", TypeAdapter(list[LibraryRssItem]), "/libraries/rss.json"
        )
        for feed in LibraryRssType
    ],
]


async def check_endpoints(
    client: httpx.AsyncClient,
    api_url: str,
    expected_versions: dict[str, str | None] | None = None,
) -> list[CheckFailure]:
    failures = []
    for check in ENDPOINTS:
        try:
            payload, response = await fetch_json(client, f"{api_url}{check.path}", check.path)
            try:
                check.adapter.validate_json(response.content, strict=True)
            except ValidationError as exc:
                raise CheckFailure(check.path, "response-schema", validation_reason(exc)) from exc
            try:
                duration = float(response.headers["X-Process-Time"])
                if not math.isfinite(duration) or duration < 0:
                    raise ValueError
                if check.counted and int(response.headers["X-Total-Count"]) != len(payload):
                    raise ValueError
                version = response.headers.get("X-Data-Commit-Hash")
                if version == "" or (
                    expected_versions is not None and version != expected_versions[check.path]
                ):
                    raise ValueError
            except (KeyError, ValueError) as exc:
                raise CheckFailure(
                    check.path, "headers", "missing or invalid timing/count/version"
                ) from exc
        except CheckFailure as exc:
            failures.append(exc)
    return failures


async def check_smoke(client: httpx.AsyncClient, api_url: str) -> list[CheckFailure]:
    api_url = api_url.rstrip("/")
    failures = []
    try:
        _, response = await fetch_json(client, f"{api_url}/ping", "/ping")
        try:
            health = PingResponse.model_validate_json(response.content, strict=True)
        except ValidationError as exc:
            raise CheckFailure("/ping", "response-schema", validation_reason(exc)) from exc
        if "no-store" not in response.headers.get("Cache-Control", "").lower():
            raise CheckFailure("/ping", "headers", "expected Cache-Control: no-store")
        required = {f"/{endpoint}" for endpoint in PREFETCH_ENDPOINTS}
        missing = required - health.datasets.keys()
        if missing:
            raise CheckFailure(
                "/ping", "readiness", f"missing datasets: {', '.join(sorted(missing))}"
            )
        if (
            not health.ready
            or health.status == "unavailable"
            or any(not dataset.usable for dataset in health.datasets.values())
        ):
            raise CheckFailure("/ping", "readiness", "one or more snapshots are unavailable")
    except CheckFailure as exc:
        failures.append(exc)
    failures.extend(await check_endpoints(client, api_url))
    return failures


async def run(api_url: str, timeout: float) -> int:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        return report(await check_smoke(client, api_url), "deployment-smoke")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="https://api.nthusa.tw")
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    return asyncio.run(run(args.api_url, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
