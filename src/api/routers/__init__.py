import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.utils.data_manager import NTHUDataManager

from . import (
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

# Global data manager instance
data_manager = NTHUDataManager(
    file_details_cache_expiry=config.FILE_DETAILS_CACHE_EXPIRY
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup: Pre-fetch configured endpoints
    print("Starting application...")
    print(f"Pre-fetching {len(config.PREFETCH_ENDPOINTS)} endpoints...")
    results = await data_manager.prefetch(config.PREFETCH_ENDPOINTS)

    success_count = sum(1 for success in results.values() if success)
    print(
        f"Pre-fetch complete: {success_count}/{len(config.PREFETCH_ENDPOINTS)} endpoints loaded"
    )

    for endpoint, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {endpoint}")

    # Initialize module-specific data processors
    print("Initializing data processors...")
    await courses.courses.update_data()
    await buses.buses.update_data()
    print("Data processors initialized.")

    yield

    # Shutdown: cleanup if needed
    print("Shutting down application...")


app = FastAPI(lifespan=lifespan)

# Using explicit origins would be safer, but for a public API that needs to be accessible from anywhere:
origins = ["*"]  # Allow all domains (Public API)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allowed origin domains list
    allow_credentials=False,  # Setting this to False when using wildcard origins
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
        "PATCH",
    ],  # Explicitly list allowed methods
    allow_headers=["*"],  # Allow all HTTP headers
    expose_headers=[
        "X-Process-Time",
        "X-Data-Commit-Hash",
    ],  # Expose custom headers used by the API
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


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
