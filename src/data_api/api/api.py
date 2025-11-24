"""
FastAPI application setup.

Creates the FastAPI app instance, configures middleware,
and registers all routers.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from data_api.core import config
from data_api.core.settings import settings
from data_api.data.manager import nthudata
from data_api.domain.buses import services as buses_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup: Pre-fetch configured endpoints
    print("Starting application...")
    print(f"Pre-fetching {len(config.PREFETCH_ENDPOINTS)} endpoints...")
    results = await nthudata.prefetch(config.PREFETCH_ENDPOINTS)

    success_count = sum(1 for success in results.values() if success)
    print(
        f"Pre-fetch complete: {success_count}/{len(config.PREFETCH_ENDPOINTS)} endpoints loaded"
    )

    for endpoint, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {endpoint}")

    # Initialize module-specific data processors
    print("Initializing data processors...")
    await buses_services.buses_service.update_data()

    from data_api.domain.courses import services as courses_services

    await courses_services.courses_service.update_data()
    print("Data processors initialized.")

    yield

    # Shutdown: cleanup if needed
    print("Shutting down application...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    app = FastAPI(
        lifespan=lifespan,
        title="NTHU Data API",
        version="1.0.0",
        description="由國立清華大學校內各單位資料所組成的公共資料 API。",
    )

    # CORS configuration
    # Using explicit origins would be safer, but for a public API:
    origins = settings.cors_origins  # From settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,  # False when using wildcard origins
        allow_methods=[
            "GET",
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
        courses,
        departments,
        dining,
        energy,
        libraries,
        locations,
        newsletters,
    )

    app.include_router(
        announcements.router, prefix="/announcements", tags=["Announcements"]
    )
    app.include_router(buses.router, prefix="/buses", tags=["Buses"])
    app.include_router(courses.router, prefix="/courses", tags=["Courses"])
    app.include_router(departments.router, prefix="/departments", tags=["Departments"])
    app.include_router(dining.router, prefix="/dining", tags=["Dining"])
    app.include_router(energy.router, prefix="/energy", tags=["Energy"])
    app.include_router(libraries.router, prefix="/libraries", tags=["Libraries"])
    app.include_router(locations.router, prefix="/locations", tags=["Locations"])
    app.include_router(newsletters.router, prefix="/newsletters", tags=["Newsletters"])

    return app


# Create the app instance
app = create_app()
