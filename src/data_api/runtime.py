"""Application-owned services and request-local REST/MCP runtime binding."""

from collections.abc import Iterator
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

import httpx
from starlette.types import ASGIApp, Receive, Scope, Send

from data_api.core.settings import settings
from data_api.data.manager import nthudata
from data_api.data.nthudata import NTHUDataManager
from data_api.domain.announcements.services import AnnouncementsService, announcements_service
from data_api.domain.buses.services import BusesService, buses_service
from data_api.domain.calendars.services import CalendarsService, calendars_service
from data_api.domain.courses.services import CoursesService, courses_service
from data_api.domain.departments.services import DepartmentsService, departments_service
from data_api.domain.dining.services import DiningService, dining_service
from data_api.domain.energy.services import EnergyService, energy_service
from data_api.domain.libraries.services import LibrariesService, ctx, libraries_service
from data_api.domain.locations.services import LocationsService, locations_service
from data_api.domain.newsletters.services import NewslettersService, newsletters_service


@dataclass
class Runtime:
    datasets: NTHUDataManager
    buses: BusesService
    courses: CoursesService
    announcements: AnnouncementsService
    calendars: CalendarsService
    departments: DepartmentsService
    dining: DiningService
    energy: EnergyService
    libraries: LibrariesService
    locations: LocationsService
    newsletters: NewslettersService

    @classmethod
    def create(cls, manager: NTHUDataManager | None = None) -> "Runtime":
        manager = manager or NTHUDataManager(
            file_details_cache_expiry=settings.file_details_cache_expiry,
            http_timeout=settings.data_http_timeout,
        )
        return cls(
            manager,
            BusesService(manager),
            CoursesService(manager),
            AnnouncementsService(manager),
            CalendarsService(manager),
            DepartmentsService(manager),
            DiningService(manager),
            EnergyService(),
            LibrariesService(manager),
            LocationsService(manager),
            NewslettersService(manager),
        )

    @asynccontextmanager
    async def lifespan(self):
        if self.datasets.fetcher.client is not None:
            raise RuntimeError("Runtime lifespan already running")
        async with AsyncExitStack() as stack:
            energy_client = await stack.enter_async_context(httpx.AsyncClient())
            library_client = await stack.enter_async_context(httpx.AsyncClient(verify=ctx))
            self.energy.client = energy_client
            self.libraries.client = library_client
            try:
                await stack.enter_async_context(self.datasets.lifespan())
                yield
            finally:
                self.energy.client = None
                self.libraries.client = None
                self.courses.reset()
                self.buses.reset()


default_runtime = Runtime(
    nthudata,
    buses_service,
    courses_service,
    announcements_service,
    calendars_service,
    departments_service,
    dining_service,
    energy_service,
    libraries_service,
    locations_service,
    newsletters_service,
)
_active_runtime: ContextVar[Runtime | None] = ContextVar("data_api_runtime", default=None)


def get_runtime() -> Runtime:
    runtime = _active_runtime.get()
    return default_runtime if runtime is None else runtime


@contextmanager
def bind_runtime(runtime: Runtime) -> Iterator[None]:
    token = _active_runtime.set(runtime)
    try:
        yield
    finally:
        _active_runtime.reset(token)


class RuntimeMiddleware:
    def __init__(self, app: ASGIApp, runtime: Runtime):
        self.app = app
        self.runtime = runtime

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        with bind_runtime(self.runtime):
            await self.app(scope, receive, send)
