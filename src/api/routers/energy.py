import datetime
import re

import httpx
from fastapi import APIRouter, HTTPException

from src.api.schemas.energy import EnergyElectricityInfo

router = APIRouter()

# 電力系統資料
ELECTRICITY_USAGE_DATA = [
    {"id": 1, "name": "北區一號", "capacity": 5200},
    {"id": 2, "name": "北區二號", "capacity": 5600},
    {"id": 3, "name": "仙宮", "capacity": 1500},
]
URL_PREFIX = "http://140.114.188.86/powermanage/fn1/kw"
URL_POSTFIX = ".aspx"


async def _fetch_electricity_data(item: dict) -> dict:
    """
    非同步獲取單個電力系統的用電資料。
    """
    url = f"{URL_PREFIX}{item['id']}{URL_POSTFIX}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Failed to get electricity usage data."
            )

        data_match = re.search(r"alt=\"kW: ([\d,-]+?)\"", response.text, re.S)
        if not data_match:
            raise HTTPException(
                status_code=500, detail="Failed to parse electricity data."
            )

        usage_value = int(data_match.group(1).replace(",", ""))
        return {
            **item,
            "data": usage_value,
            "unit": "kW",
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


async def _get_realtime_electricity_usage():
    """
    非同步獲取所有電力系統的即時用電資料。
    """
    import asyncio

    tasks = [_fetch_electricity_data(item.copy()) for item in ELECTRICITY_USAGE_DATA]
    return await asyncio.gather(*tasks)


@router.get("/electricity_usage", response_model=list[EnergyElectricityInfo])
async def get_realtime_electricity_usage():
    """
    取得校園電力即時使用量。
    資料來源：[校園能源查詢管理系統](http://140.114.188.86/powermanage/index.aspx)
    """
    try:
        return await _get_realtime_electricity_usage()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
