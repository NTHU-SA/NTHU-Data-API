"""
Energy domain service.

Handles real-time electricity usage data fetching.
"""

import asyncio
import datetime
import re

import httpx

# Electricity system data
ELECTRICITY_USAGE_DATA = [
    {"id": 1, "name": "北區一號", "capacity": 5200},
    {"id": 2, "name": "北區二號", "capacity": 5600},
    {"id": 3, "name": "仙宮", "capacity": 1500},
]
URL_PREFIX = "http://140.114.188.86/powermanage/fn1/kw"
URL_POSTFIX = ".aspx"


async def fetch_electricity_data(item: dict) -> dict:
    """Async fetch electricity data for one system."""
    url = f"{URL_PREFIX}{item['id']}{URL_POSTFIX}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                "Failed to fetch electricity data.",
                request=response.request,
                response=response,
            )

        data_match = re.search(r"alt=\"kW: ([\d,-]+?)\"", response.text, re.S)
        if not data_match:
            raise ValueError("Failed to parse electricity data.")

        usage_value = int(data_match.group(1).replace(",", ""))
        return {
            **item,
            "data": usage_value,
            "unit": "kW",
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


class EnergyService:
    """Service for energy data operations."""

    async def get_realtime_electricity_usage(self) -> list[dict]:
        """Get real-time electricity usage for all systems."""
        tasks = [fetch_electricity_data(item.copy()) for item in ELECTRICITY_USAGE_DATA]
        return await asyncio.gather(*tasks)


# Global service instance
energy_service = EnergyService()
