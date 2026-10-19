"""Readiness based on existing snapshots, without upstream probes."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Response

from data_api.api.schemas.ping import DatasetError, DatasetHealth, PingResponse
from data_api.core.config import PREFETCH_ENDPOINTS
from data_api.data.nthudata import DatasetState, Freshness
from data_api.runtime import get_runtime

router = APIRouter()


def _build_dataset_health(state: DatasetState | None, now: float) -> DatasetHealth:
    if state is None:
        return DatasetHealth()
    snapshot = state.snapshot
    error = state.last_error
    return DatasetHealth(
        usable=state.usable,
        freshness=state.freshness,
        check_due=state.last_checked_at is None or now >= state.next_check,
        version=snapshot.version if snapshot else None,
        loaded_at=snapshot.loaded_at if snapshot else None,
        published_at=snapshot.published_at if snapshot else None,
        last_checked_at=state.last_checked_at,
        last_refresh_attempt_at=state.last_refresh_attempt_at,
        last_refresh_success_at=state.last_refresh_success_at,
        last_error=(
            DatasetError(category=error.category, at=error.at, status_code=error.status_code)
            if error
            else None
        ),
    )


def _readiness_status(ready: bool, healthy: bool) -> Literal["ok", "degraded", "unavailable"]:
    if not ready:
        return "unavailable"
    return "ok" if healthy else "degraded"


@router.get("/ping", include_in_schema=False)
async def ping(response: Response) -> PingResponse:
    nthudata = get_runtime().datasets
    now = nthudata.clock()
    endpoints = {f"/{endpoint}" for endpoint in PREFETCH_ENDPOINTS} | nthudata.states.keys()
    datasets = {
        endpoint: _build_dataset_health(nthudata.states.get(endpoint), now)
        for endpoint in sorted(endpoints)
    }

    ready = all(dataset.usable for dataset in datasets.values())
    healthy = all(
        dataset.freshness == Freshness.CURRENT and not dataset.check_due
        for dataset in datasets.values()
    )
    response.status_code = 200 if ready else 503
    response.headers["Cache-Control"] = "no-store"
    return PingResponse(
        status=_readiness_status(ready, healthy),
        ready=ready,
        checked_at=datetime.now(timezone.utc),
        datasets=datasets,
    )


@router.head("/ping", include_in_schema=False)
async def ping_head() -> Response:
    response = Response(media_type="application/json")
    await ping(response)
    # An empty HEAD body must not advertise a zero-length GET representation.
    del response.headers["Content-Length"]
    return response
