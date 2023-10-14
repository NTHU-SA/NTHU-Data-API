from .. import app
from .routers import lib, phones, rpage, questions, locations

app.include_router(lib.router)
app.include_router(rpage.router)
app.include_router(phones.router)
app.include_router(questions.router)
app.include_router(locations.router)
