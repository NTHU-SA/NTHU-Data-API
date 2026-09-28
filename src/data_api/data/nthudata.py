"""Disposable, instance-local snapshots of the authoritative published datasets."""

import asyncio
import hashlib
import json
import logging
import os
import socket
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from data_api.core.exceptions import DataNotAvailableException

logger = logging.getLogger(__name__)
JsonData = dict | list
T = TypeVar("T")


class Freshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNVERIFIED = "unverified"
    UNAVAILABLE = "unavailable"


class FetchFailure(Exception):
    """An expected upstream failure; never stores response bodies or credentials."""

    def __init__(self, category: str, status_code: int | None = None):
        super().__init__(category)
        self.category = category
        self.status_code = status_code


@dataclass(frozen=True)
class RefreshError:
    category: str
    at: datetime
    status_code: int | None = None


@dataclass(frozen=True)
class Snapshot(Generic[T]):
    raw: JsonData
    data: T
    version: str | None
    loaded_at: datetime
    published_at: str | None = None


@dataclass
class DatasetState(Generic[T]):
    prepare: Callable[[JsonData], T]
    snapshot: Snapshot[T] | None = None
    last_checked_at: datetime | None = None
    last_refresh_attempt_at: datetime | None = None
    last_refresh_success_at: datetime | None = None
    last_error: RefreshError | None = None
    freshness: Freshness = Freshness.UNAVAILABLE
    next_check: float = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def usable(self) -> bool:
        return self.snapshot is not None


class DataFetcher:
    """Reuse the client owned by the application lifespan."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client: httpx.AsyncClient | None = None

    async def fetch_json(self, url: str, sha256: str | None = None) -> JsonData:
        if self.client is None:
            raise FetchFailure("client_unavailable")
        try:
            response = await self.client.get(url)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise FetchFailure("timeout") from exc
        except httpx.HTTPStatusError as exc:
            raise FetchFailure("http_status", exc.response.status_code) from exc
        except httpx.ConnectError as exc:
            cause: BaseException | None = exc
            while cause is not None:
                if isinstance(cause, socket.gaierror):
                    raise FetchFailure("dns") from exc
                cause = cause.__cause__ or cause.__context__
            raise FetchFailure("connection") from exc
        except httpx.RequestError as exc:
            raise FetchFailure("request") from exc

        if sha256 is not None and hashlib.sha256(response.content).hexdigest() != sha256:
            raise FetchFailure("checksum")
        try:
            data = response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise FetchFailure("invalid_json") from exc
        if not isinstance(data, (dict, list)):
            raise FetchFailure("payload_type")
        return data


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    name: str = Field(min_length=1)
    last_commit: str | None = Field(default=None, min_length=1)
    version: str | None = Field(default=None, min_length=1)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    last_updated: str | None = None

    @property
    def active_version(self) -> str | None:
        return self.last_commit or self.version


class PublishedManifest(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    file_details: dict[str, list[ManifestEntry]]


class FileDetailsManager:
    """Cache successful checks AND failures, without presenting old metadata as fresh."""

    def __init__(
        self,
        fetcher: DataFetcher,
        file_details_url: str,
        cache_expiry: float = 300,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.fetcher = fetcher
        self.file_details_url = file_details_url
        self.cache_expiry = cache_expiry
        self.clock = clock
        self.entries: dict[str, ManifestEntry] = {}
        self.error: RefreshError | None = None
        self.checked_at: datetime | None = None
        self.next_check = 0.0
        self.lock = asyncio.Lock()

    async def check(self) -> None:
        if self.checked_at is not None and self.clock() < self.next_check:
            return
        async with self.lock:
            if self.checked_at is not None and self.clock() < self.next_check:
                return
            try:
                raw = await self.fetcher.fetch_json(self.file_details_url)
                try:
                    manifest = PublishedManifest.model_validate(raw)
                    entries = {}
                    for section, files in manifest.file_details.items():
                        for entry in files:
                            path = "/" + "/".join(
                                part for part in (section.strip("/"), entry.name) if part
                            )
                            if path in entries:
                                raise FetchFailure("manifest_parsing")
                            entries[path] = entry
                except ValidationError as exc:
                    raise FetchFailure("manifest_parsing") from exc
            except FetchFailure as exc:
                category = (
                    "manifest_parsing"
                    if exc.category in {"invalid_json", "payload_type"}
                    else exc.category
                )
                self.error = RefreshError(category, datetime.now(timezone.utc), exc.status_code)
                self.entries = {}
                logger.warning(
                    "manifest check failed category=%s status=%s", category, exc.status_code
                )
            else:
                self.entries = entries
                self.error = None
                logger.debug("manifest checked")
            self.checked_at = datetime.now(timezone.utc)
            self.next_check = self.clock() + self.cache_expiry


class NTHUDataManager:
    """One manager per running process; no disk cache or cross-instance coordination."""

    def __init__(
        self,
        base_url: str | None = None,
        file_details_cache_expiry: float = 300,
        http_timeout: float = 15,
        clock: Callable[[], float] = time.monotonic,
    ):
        if file_details_cache_expiry <= 0 or http_timeout <= 0:
            raise ValueError("TTL and HTTP timeout must be positive")
        self.base_url = (base_url or os.getenv("NTHU_DATA_URL", "https://data.nthusa.tw")).rstrip(
            "/"
        )
        self.ttl = file_details_cache_expiry
        self.http_timeout = http_timeout
        self.clock = clock
        self.fetcher = DataFetcher(self.base_url)
        self.file_details_manager = FileDetailsManager(
            self.fetcher, f"{self.base_url}/file_details.json", self.ttl, clock
        )
        self.states: dict[str, DatasetState[Any]] = {}

    def register(self, endpoint: str, prepare: Callable[[JsonData], T]) -> DatasetState[T]:
        key = self._normalize_endpoint_name(endpoint)
        if key in self.states:
            raise ValueError(f"Dataset already registered: {key}")
        state = DatasetState(prepare)
        self.states[key] = state
        return state

    @asynccontextmanager
    async def lifespan(self, client: httpx.AsyncClient | None = None):
        """Own and close the shared client, including on failed startup."""
        if self.fetcher.client is not None:
            raise RuntimeError("Data manager lifespan already running")
        self.reset()
        async with (
            client
            or httpx.AsyncClient(
                http2=True, timeout=httpx.Timeout(self.http_timeout), follow_redirects=True
            ) as active_client
        ):
            self.fetcher.client = active_client
            try:
                yield self
            finally:
                self.fetcher.client = None
                self.reset()

    def reset(self) -> None:
        """A new instance has no last-known-good from its predecessor."""
        for state in self.states.values():
            state.snapshot = None
            state.last_checked_at = None
            state.last_refresh_attempt_at = None
            state.last_refresh_success_at = None
            state.last_error = None
            state.freshness = Freshness.UNAVAILABLE
            state.next_check = 0
            state.lock = asyncio.Lock()
        self.file_details_manager = FileDetailsManager(
            self.fetcher, f"{self.base_url}/file_details.json", self.ttl, self.clock
        )

    def state_for(self, endpoint: str) -> DatasetState:
        key = self._normalize_endpoint_name(endpoint)
        if key not in self.states:
            from data_api.data.validation import validate_dataset

            self.register(key, lambda raw: validate_dataset(key, raw))
        return self.states[key]

    async def get_snapshot(self, endpoint: str, state: DatasetState[T]) -> Snapshot[T]:
        if state.lock.locked() or state.last_checked_at is None or self.clock() >= state.next_check:
            async with state.lock:
                if state.last_checked_at is None or self.clock() >= state.next_check:
                    completed = False
                    try:
                        await self._refresh(self._normalize_endpoint_name(endpoint), state)
                        completed = True
                    finally:
                        if not completed:
                            state.next_check = 0
        if state.snapshot is None:
            raise DataNotAvailableException(
                "Dataset temporarily unavailable. Please try again later."
            )
        return state.snapshot

    async def _refresh(self, endpoint: str, state: DatasetState[T]) -> None:
        previous = state.snapshot
        logger.debug("dataset check due dataset=%s", endpoint)
        manifest = self.file_details_manager
        await manifest.check()
        state.last_checked_at = manifest.checked_at
        entry = manifest.entries.get(endpoint)
        version = entry.active_version if entry else None
        error = manifest.error
        if error is None and version is None:
            error = RefreshError("version_unknown", datetime.now(timezone.utc))
        # Anchor to the actual manifest check, not this reader's access time.
        state.next_check = manifest.next_check
        if error is not None and previous is not None:
            state.last_error = error
            state.freshness = Freshness.UNVERIFIED
            logger.warning(
                "dataset unverified, keeping snapshot dataset=%s category=%s",
                endpoint,
                error.category,
            )
            return
        if version is not None and previous is not None and previous.version == version:
            state.last_error = None
            state.freshness = Freshness.CURRENT
            logger.debug("dataset version unchanged dataset=%s version=%s", endpoint, version)
            return

        state.last_refresh_attempt_at = datetime.now(timezone.utc)
        logger.info(
            "dataset load started dataset=%s previous=%s new=%s",
            endpoint,
            previous.version if previous else None,
            version,
        )
        try:
            raw, candidate = await self._load_candidate(endpoint, state, entry)
        except FetchFailure as exc:
            state.last_error = RefreshError(
                exc.category, datetime.now(timezone.utc), exc.status_code
            )
            state.freshness = Freshness.STALE if previous is not None else Freshness.UNAVAILABLE
            logger.warning(
                "dataset load failed dataset=%s category=%s status=%s usable=%s",
                endpoint,
                exc.category,
                exc.status_code,
                state.usable,
            )
            # Bound retry storms even when the first load has no fallback.
            state.next_check = max(state.next_check, self.clock() + self.ttl)
        else:
            now = datetime.now(timezone.utc)
            state.snapshot = Snapshot(
                raw, candidate, version, now, entry.last_updated if entry else None
            )
            state.last_refresh_success_at = now
            state.last_error = error
            state.freshness = Freshness.UNVERIFIED if error else Freshness.CURRENT
            logger.info(
                "dataset load succeeded dataset=%s version=%s freshness=%s",
                endpoint,
                version,
                state.freshness,
            )

    async def _load_candidate(
        self, endpoint: str, state: DatasetState[T], entry: ManifestEntry | None
    ) -> tuple[JsonData, T]:
        raw = await self.fetcher.fetch_json(
            f"{self.base_url}{endpoint}", entry.sha256 if entry else None
        )
        try:
            return raw, state.prepare(raw)
        except ValidationError as exc:
            raise FetchFailure("validation") from exc
        except ValueError as exc:
            raise FetchFailure("transformation") from exc

    async def get(self, endpoint_name: str) -> tuple[str | None, JsonData]:
        snapshot = await self.get_snapshot(endpoint_name, self.state_for(endpoint_name))
        return snapshot.version, snapshot.raw

    async def prefetch(self, endpoints: list[str]) -> dict[str, bool]:
        async def load(endpoint: str) -> bool:
            try:
                await self.get(endpoint)
            except DataNotAvailableException:
                return False
            return True

        tasks = {}
        async with asyncio.TaskGroup() as group:
            for endpoint in endpoints:
                tasks[endpoint] = group.create_task(load(endpoint))
        return {endpoint: task.result() for endpoint, task in tasks.items()}

    @staticmethod
    def _normalize_endpoint_name(endpoint_name: str) -> str:
        return "/" + endpoint_name.lstrip("/")
