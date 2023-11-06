from fastapi import APIRouter

from .events import router as events_router
from .careers import router as careers_router

router = APIRouter()
router.include_router(events_router, prefix="/events", tags=["Events"])
router.include_router(careers_router, prefix="/careers", tags=["Careers"])
