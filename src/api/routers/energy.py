from fastapi import APIRouter, HTTPException

from src.api import schemas
from src.api.models.energy import Energy

router = APIRouter()
energy = Energy()


@router.get("/electricity_usage", response_model=list[schemas.energy.ElectricityInfo])
async def get_realtime_electricity_usage():
    """
    取得校園電力即時使用量。
    """
    try:
        return energy.get_realtime_electricity_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
