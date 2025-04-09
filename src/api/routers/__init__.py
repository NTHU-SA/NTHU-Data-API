import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI()

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
