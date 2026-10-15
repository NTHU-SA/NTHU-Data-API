"""Energy router."""

from fastapi import APIRouter

from data_api.api.errors import service_errors
from data_api.api.schemas import energy as schemas
from data_api.api.schemas.errors import LIVE_ERROR_RESPONSES
from data_api.runtime import get_runtime

router = APIRouter()


@router.get(
    "/electricity",
    response_model=list[schemas.EnergyElectricityInfo],
    operation_id="getElectricity",
    responses=LIVE_ERROR_RESPONSES,
)
async def get_realtime_electricity_usage():
    """
    取得校園電力即時使用量。
    資料來源：[校園能源查詢管理系統](http://140.114.188.86/powermanage/index.aspx)
    """
    with service_errors():
        return await get_runtime().energy.get_realtime_electricity_usage()
