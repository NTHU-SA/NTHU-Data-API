import time

from fastapi import FastAPI, Request

from .api.routers import (
    buses,
    contacts,
    courses,
    dining,
    energy,
    libraries,
    locations,
    newsletters,
    resources,
    scrapers,
)

app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.include_router(buses.router, prefix="/buses", tags=["Buses"])
app.include_router(courses.router, prefix="/courses", tags=["Courses"])
app.include_router(dining.router, prefix="/dining", tags=["Dining"])
app.include_router(energy.router, prefix="/energy", tags=["Energy"])
app.include_router(libraries.router, prefix="/libraries", tags=["Libraries"])
app.include_router(locations.router, prefix="/locations", tags=["Locations"])
app.include_router(newsletters.router, prefix="/newsletters", tags=["Newsletters"])
app.include_router(contacts.router, prefix="/phones", tags=["Phones"])
app.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
app.include_router(resources.router, prefix="/resources", tags=[])
app.include_router(scrapers.router, prefix="/scrapers", tags=["Scrapers"])


@app.get(
    "/",
    responses={
        200: {
            "description": "測試 API 是否正常運作",
            "content": {
                "application/json": {"example": {"message": "Hello World!"}},
            },
        },
    },
)
async def home():
    return {"message": "Hello World!"}


@app.get(
    "/ping",
    responses={
        200: {
            "description": "測試 API 是否正常運作",
            "content": {
                "application/json": {"example": {"message": "pong"}},
            },
        },
    },
)
async def ping():
    return {"message": "pong"}
