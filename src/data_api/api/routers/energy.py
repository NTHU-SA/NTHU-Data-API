"""Energy router."""

from fastapi import APIRouter, HTTPException

from data_api.api.schemas import energy as schemas
from data_api.domain.energy import services

router = APIRouter()


@router.get("/electricity_usage", response_model=list[schemas.EnergyElectricityInfo])
async def get_realtime_electricity_usage():
    """
    Get real-time campus electricity usage.
    Data source: Campus Energy Management System
    """
    try:
        return await services.energy_service.get_realtime_electricity_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
