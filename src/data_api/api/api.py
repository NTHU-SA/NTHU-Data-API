"""
FastAPI application setup.

Creates the FastAPI app instance, configures middleware,
and registers all routers.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from data_api.api.schemas.meta import MetaResponse
from data_api.core import config
from data_api.core.exceptions import (
    INTERNAL_ERROR_DETAIL,
    DataNotAvailableException,
    UpstreamException,
)
from data_api.core.settings import settings
from data_api.data.manager import nthudata
from data_api.domain.buses import services as buses_services
from data_api.mcp import mcp

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    from data_api.domain.courses import services as courses_services

    async with nthudata.lifespan():
        app.state.datasets = nthudata
        results = await nthudata.prefetch(config.PREFETCH_ENDPOINTS)
        logging.getLogger(__name__).info(
            "Data startup: %s/%s datasets usable", sum(results.values()), len(results)
        )
        for service in (buses_services.buses_service, courses_services.courses_service):
            try:
                await service.update_data()
            except DataNotAvailableException:
                # The manager records the failure. Other datasets must remain available.
                continue
        yield


# MCP's session manager must run alongside the data initialization lifespan.
mcp_app = mcp.http_app(path="/mcp", transport="streamable-http", stateless_http=True)


@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    """Run both MCP and data lifespans on the exported application."""
    async with mcp_app.lifespan(app):
        async with lifespan(app):
            yield


class _SafeUnexpectedErrorsMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def track_response(message: Message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, track_response)
        except Exception as exc:
            if response_started:
                raise
            logger.error("Unexpected request failure", exc_info=exc)
            await JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR_DETAIL})(
                scope, receive, send
            )


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    app = FastAPI(
        lifespan=combined_lifespan,
        routes=list(mcp_app.routes),
        title="NTHU Data API",
        version="2.0.0",
        description="由國立清華大學校內各單位資料所組成的公共資料 API。",
    )

    @app.exception_handler(DataNotAvailableException)
    async def dataset_unavailable(request: Request, exc: DataNotAvailableException):
        return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable"})

    @app.exception_handler(UpstreamException)
    async def upstream_failure(request: Request, exc: UpstreamException):
        logger.warning("Live upstream request failed", exc_info=exc)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logger.error("Unexpected request failure", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR_DETAIL})

    # CORS and timing wrap this fallback so pre-response errors keep their headers.
    app.add_middleware(_SafeUnexpectedErrorsMiddleware)

    # CORS configuration
    # Using explicit origins would be safer, but for a public API:
    origins = settings.cors_origins  # From settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,  # False when using wildcard origins
        allow_methods=[
            "GET",
            "HEAD",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
            "PATCH",
        ],
        allow_headers=["*"],
        expose_headers=[
            "X-Process-Time",
            "X-Data-Commit-Hash",
            "X-Total-Count",
        ],
    )

    # Process time middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    @app.get("/", response_model=MetaResponse, operation_id="getApiMetadata", tags=["Metadata"])
    async def metadata() -> MetaResponse:
        """Discover the API name, version, documentation, and MCP endpoint."""
        return MetaResponse(
            name=app.title,
            version=app.version,
            docs="/docs",
            openapi="/openapi.json",
            mcp="/mcp",
        )

    # Add favicon route
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Favicon route."""
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="https://www.nthu.edu.tw/favicon.ico")

    # Register routers
    from data_api.api.routers import (
        announcements,
        buses,
        calendars,
        courses,
        departments,
        dining,
        directory,
        energy,
        libraries,
        locations,
        newsletters,
        ping,
    )

    app.include_router(ping.router)
    app.include_router(announcements.router, prefix="/announcements", tags=["Announcements"])
    app.include_router(buses.router, prefix="/buses", tags=["Buses"])
    app.include_router(calendars.router, prefix="/calendars", tags=["Calendars"])
    app.include_router(courses.router, prefix="/courses", tags=["Courses"])
    app.include_router(departments.router, prefix="/departments", tags=["Departments"])
    app.include_router(directory.router, prefix="/directory", tags=["Directory"])
    app.include_router(dining.router, prefix="/dining", tags=["Dining"])
    app.include_router(energy.router, prefix="/energy", tags=["Energy"])
    app.include_router(libraries.router, prefix="/libraries", tags=["Libraries"])
    app.include_router(locations.router, prefix="/locations", tags=["Locations"])
    app.include_router(newsletters.router, prefix="/newsletters", tags=["Newsletters"])

    return app


app = create_app()

# Preserve module aliases without constructing a second, unconfigured app.
fast_api_app = combined_app = app
