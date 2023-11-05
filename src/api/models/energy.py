import re
import requests
import json
import datetime
from cachetools import cached, TTLCache


class Energy:
    # 電力系統
    # http://140.114.188.57/nthu2020/Index.aspx
    @cached(cache=TTLCache(maxsize=14, ttl=60))
    def get_realtime_electricity_usage(self):
        URL_PREFIX = "http://140.114.188.57/nthu2020/fn1/kw"
        URL_POSTFIX = ".aspx"

        data_names = ["北區一號", "北區二號", "仙宮"]
        data_capacities = [5200, 5600, 1500]
        electricity_usage_data = []

        for i in range(1, 4):
            res = requests.get(URL_PREFIX + str(i) + URL_POSTFIX)
            res_text = res.text

            data = re.search(r"alt=\"kW: ([\d,-]+?)\"", res_text, re.S).group(1)

            unit_data = {}
            unit_data["name"] = data_names[i - 1]
            unit_data["data"] = int(data.replace(",", ""))
            unit_data["capacity"] = data_capacities[i - 1]
            unit_data["unit"] = "kW"
            unit_data["last_updated"] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            electricity_usage_data.append(unit_data)

        return electricity_usage_data


if __name__ == "__main__":
    energy = Energy()
    json_data = energy.get_realtime_electricity_usage()

    with open("data/energy_sys.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
