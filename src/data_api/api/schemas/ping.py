"""Read-only dataset readiness diagnostics."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from data_api.data.nthudata import Freshness


class DatasetError(BaseModel):
    category: str
    at: datetime
    status_code: int | None = None


class DatasetHealth(BaseModel):
    usable: bool = False
    freshness: Freshness = Freshness.UNAVAILABLE
    check_due: bool = True
    version: str | None = None
    loaded_at: datetime | None = None
    published_at: str | None = None
    last_checked_at: datetime | None = None
    last_refresh_attempt_at: datetime | None = None
    last_refresh_success_at: datetime | None = None
    last_error: DatasetError | None = None


class PingResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    ready: bool
    checked_at: datetime
    datasets: dict[str, DatasetHealth]
