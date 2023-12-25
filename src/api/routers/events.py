from fastapi import APIRouter

from src.api import schemas
from src.api.models.events import get_events_list

router = APIRouter()


@router.get("/", response_model=dict[str, list[schemas.events.EventData]])
async def get_events():
    """
    取得所有活動資料。
    """
    return get_events_list()


@router.get("/{event_type}", response_model=list[schemas.events.EventData])
async def get_events_by_type(event_type: schemas.events.EventTypes):
    """
    取得特定類型的活動資料。
    """
    return get_events_list()[event_type]
