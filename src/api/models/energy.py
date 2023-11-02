import re
import requests
import json
import datetime

from cachetools import cached, TTLCache


class Energy:
    # 電力系統
    # http://140.114.188.57/nthu2020/Index.aspx
    def _get_response(self, url: str):
        headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-CN;q=0.5",
            "dnt": "1",
            "referer": url,
            "sec-ch-ua": "'Chromium';v='112', 'Microsoft Edge';v='112', 'Not:A-Brand';v='99'",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "Android",
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36 Edg/112.0.1722.48",
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception("Request Error")
        response_text = response.text
        return response_text

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
