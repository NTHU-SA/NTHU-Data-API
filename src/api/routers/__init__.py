import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import (
    bulletins,
    buses,
    contacts,
    courses,
    dining,
    energy,
    events,
    libraries,
    locations,
    newsletters,
    scrapers,
)

app = FastAPI()

origins = ["*"]  # 允許來自所有網域 (Public API)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允許的來源網域列表
    allow_credentials=True,  # 允許跨域請求帶有 Cookie 和 HTTP 認證資訊
    allow_methods=["*"],  # 允許所有 HTTP 方法 (GET, POST, PUT, DELETE 等)
    allow_headers=["*"],  # 允許所有 HTTP 標頭
)


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
app.include_router(scrapers.router, prefix="/scrapers", tags=["Scrapers"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(bulletins.router, prefix="/bulletins", tags=["Bulletins"])


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
async def hello_world():
    return {"message": "Hello World!"}
