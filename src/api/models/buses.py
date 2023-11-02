import requests
import re
import json

from cachetools import cached, TTLCache


class Buses:
    # 校本部公車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw
    # 南大區間車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw
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

    @cached(cache=TTLCache(maxsize=14, ttl=60 * 60))
    def get_nanda_data(self):
        url = "https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw"
        res_text = self._get_response(url)

        def get_campus_info(variable_string: str):
            regex_pattern = r"const " + variable_string + " = (\{.*?\})"
            data = re.search(regex_pattern, res_text, re.S).group(1)
            data = data.replace("'", '"')
            data = data.replace("\n", "")
            data = data.replace("direction", '"direction"')
            data = data.replace("duration", '"duration"')
            data = data.replace("route", '"route"', 1)
            data = data.replace("routeEN", '"routeEN"')
            data = json.loads(data)
            return data

        def get_bus_schedule(variable_string: str):
            regex_pattern = r"const " + variable_string + " = (\[.*?\])"
            data = re.search(regex_pattern, res_text, re.S).group(1)
            data = data.replace("'", '"')
            data = data.replace("\n", "")
            data = data.replace("time", '"time"')
            data = data.replace("description", '"description"')
            data = data.replace(",    ]", "]")
            data = json.loads(data)
            return data

        # 往南大校區資訊
        toward_south_campus_info = get_campus_info("towardSouthCampusInfo")

        # 往南大校區時刻表(平日)
        weekday_bus_schedule_toward_south_campus = get_bus_schedule(
            "weekdayBusScheduleTowardSouthCampus"
        )

        # 往南大校區時刻表(假日)
        weekend_bus_schedule_toward_south_campus = get_bus_schedule(
            "weekendBusScheduleTowardSouthCampus"
        )

        # 往校本部資訊
        toward_main_campus_info = get_campus_info("towardMainCampusInfo")

        # 往校本部時刻表(平日)
        weekday_bus_schedule_toward_main_campus = get_bus_schedule(
            "weekdayBusScheduleTowardMainCampus"
        )

        # 往校本部時刻表(假日)
        weekend_bus_schedule_toward_main_campus = get_bus_schedule(
            "weekendBusScheduleTowardMainCampus"
        )

        # 輸出 json 檔案
        nanda_dataset = {
            "toward_south_campus_info": toward_south_campus_info,
            "weekday_bus_schedule_toward_south_campus": weekday_bus_schedule_toward_south_campus,
            "weekend_bus_schedule_toward_south_campus": weekend_bus_schedule_toward_south_campus,
            "toward_main_campus_info": toward_main_campus_info,
            "weekday_bus_schedule_toward_main_campus": weekday_bus_schedule_toward_main_campus,
            "weekend_bus_schedule_toward_main_campus": weekend_bus_schedule_toward_main_campus,
        }

        return nanda_dataset


if __name__ == "__main__":
    buses = Buses()
    json_data = buses.get_nanda_data()
    with open("data/buses_nanda.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
