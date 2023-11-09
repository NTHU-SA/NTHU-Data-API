from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models.energy import Energy


class ElectricityInfo(BaseModel):
    name: str = Field(..., description="電力名稱")
    data: int = Field(..., description="電力使用量")
    capacity: int = Field(..., description="電力容量")
    unit: str = Field(..., description="單位")
    last_updated: str = Field(..., description="最後更新時間")


router = APIRouter()
energy = Energy()


@router.get("/electricity_usage", response_model=list[ElectricityInfo])
async def get_realtime_electricity_usage():
    """
    取得校園電力即時使用量。
    """
    try:
        return energy.get_realtime_electricity_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
