from .. import app
from .routers import (
    buses,
    courses,
    dining,
    energy,
    libraries,
    locations,
    newsletters,
    phones,
    resources,
    rpage,
)

app.include_router(buses.router, prefix="/buses", tags=["Buses"])
app.include_router(courses.router, prefix="/courses", tags=["Courses"])
app.include_router(dining.router, prefix="/dining", tags=["Dining"])
app.include_router(energy.router, prefix="/energy", tags=["Energy"])
app.include_router(libraries.router, prefix="/libraries", tags=["Libraries"])
app.include_router(locations.router, prefix="/locations", tags=["Locations"])
app.include_router(newsletters.router, prefix="/newsletters", tags=["Newsletters"])
app.include_router(phones.router, prefix="/phones", tags=["Phones"])
app.include_router(resources.router, prefix="/resources", tags=[])
app.include_router(rpage.router, prefix="/rpage", tags=["Rpage"])
