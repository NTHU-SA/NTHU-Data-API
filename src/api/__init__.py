from .. import app
from .routers import lib, phones, rpage, locations, buses, dining, energy, courses

app.include_router(lib.router)
app.include_router(rpage.router)
app.include_router(phones.router)
app.include_router(locations.router)
app.include_router(buses.router)
app.include_router(dining.router)
app.include_router(energy.router)
app.include_router(courses.router)
