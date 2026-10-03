"""Readiness based on existing snapshots, without upstream probes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Response

from data_api.api.schemas.ping import DatasetError, DatasetHealth, PingResponse
from data_api.core.config import PREFETCH_ENDPOINTS
from data_api.data.manager import nthudata
from data_api.data.nthudata import Freshness

router = APIRouter()


@router.get("/ping", response_model=PingResponse, include_in_schema=False)
async def ping(response: Response) -> PingResponse:
    now = nthudata.clock()
    endpoints = {f"/{endpoint}" for endpoint in PREFETCH_ENDPOINTS} | nthudata.states.keys()
    datasets: dict[str, DatasetHealth] = {}
    for endpoint in sorted(endpoints):
        state = nthudata.states.get(endpoint)
        if state is None:
            datasets[endpoint] = DatasetHealth()
            continue
        snapshot = state.snapshot
        error = state.last_error
        datasets[endpoint] = DatasetHealth(
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

    ready = all(dataset.usable for dataset in datasets.values())
    healthy = all(
        dataset.freshness == Freshness.CURRENT and not dataset.check_due
        for dataset in datasets.values()
    )
    response.status_code = 200 if ready else 503
    response.headers["Cache-Control"] = "no-store"
    return PingResponse(
        status=("ok" if healthy else "degraded") if ready else "unavailable",
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
