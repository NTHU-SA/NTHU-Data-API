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


@router.get(
    "/electricity_usage",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "name": "北區一號",
                            "data": 2027,
                            "capacity": 5200,
                            "unit": "kW",
                            "last_updated": "2023-11-03 03:06:12",
                        },
                        {
                            "name": "北區二號",
                            "data": -999,
                            "capacity": 5600,
                            "unit": "kW",
                            "last_updated": "2023-11-03 03:06:12",
                        },
                        {
                            "name": "仙宮",
                            "data": 683,
                            "capacity": 1500,
                            "unit": "kW",
                            "last_updated": "2023-11-03 03:06:12",
                        },
                    ]
                },
            },
        },
    },
    response_model=list[ElectricityInfo],
)
async def get_realtime_electricity_usage():
    """
    取得校園電力即時使用量。
    """
    try:
        return energy.get_realtime_electricity_usage()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
