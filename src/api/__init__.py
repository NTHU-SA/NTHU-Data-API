from .. import app
from .routers import (
    lib,
    phones,
    resources,
    rpage,
    locations,
    buses,
    dining,
    energy,
    courses,
)

app.include_router(
    lib.router,
    prefix="/lib",
    tags=["Library"],
)
app.include_router(
    rpage.router,
    prefix="/rpage",
    tags=["Rpage"],
)
app.include_router(
    phones.router,
    prefix="/phones",
    tags=["Phones"],
)
app.include_router(
    locations.router,
    prefix="/locations",
    tags=["locations"],
)
app.include_router(
    buses.router,
    prefix="/buses",
    tags=["buses"],
)
app.include_router(
    dining.router,
    prefix="/dining",
    tags=["dining"],
)
app.include_router(
    energy.router,
    prefix="/energy",
    tags=["energy"],
)
app.include_router(courses.router, prefix="/courses", tags=["courses"])
app.include_router(resources.router, prefix="/resources", tags=[])
