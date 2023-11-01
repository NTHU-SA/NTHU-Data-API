from .. import app
from .routers import lib, phones, rpage, locations

app.include_router(lib.router)
app.include_router(rpage.router)
app.include_router(phones.router)
app.include_router(locations.router)
