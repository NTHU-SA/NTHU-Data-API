from fastapi import APIRouter, HTTPException
from ..models.energy import Energy

router = APIRouter(
    prefix="/energy",
    tags=["energy"],
    responses={404: {"description": "Not found"}},
)

energy = Energy()


@router.get("/electricity_usage")
def get_realtime_electricity_usage():
    try:
        return energy.get_realtime_electricity_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
