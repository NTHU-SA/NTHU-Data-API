import datetime
import re

import requests
from cachetools import TTLCache, cached
from fastapi import HTTPException


class Energy:
    # 電力系統
    # 舊版: http://140.114.188.57/nthu2020/Index.aspx
    # 新版: http://140.114.188.86/powermanage/index.aspx
    @cached(cache=TTLCache(maxsize=14, ttl=60))
    def get_realtime_electricity_usage(self):
        URL_PREFIX = "http://140.114.188.86/powermanage/fn1/kw"
        URL_POSTFIX = ".aspx"

        electricity_usage_data = [
            {"id": 1, "name": "北區一號", "capacity": 5200},
            {"id": 2, "name": "北區二號", "capacity": 5600},
            {"id": 3, "name": "仙宮", "capacity": 1500},
        ]

        for item in electricity_usage_data:
            res = requests.get(URL_PREFIX + str(item["id"]) + URL_POSTFIX)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Failed to get electricity usage data."
                )
            res_text = res.text

            data = re.search(r"alt=\"kW: ([\d,-]+?)\"", res_text, re.S)
            if data is not None:
                data = data.group(1)
            else:
                return None

            item.update(
                {
                    "data": int(data.replace(",", "")),
                    "unit": "kW",
                    "last_updated": datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )

        return electricity_usage_data
