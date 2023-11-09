from fastapi import APIRouter

from .careers import router as careers_router
from .events import router as events_router

router = APIRouter()
router.include_router(events_router, prefix="/events", tags=["Events"])
router.include_router(careers_router, prefix="/careers", tags=["Careers"])
