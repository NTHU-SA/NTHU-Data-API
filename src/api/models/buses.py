import requests
import re
import json

from src.utils import cached_request


class Buses:
    # 校本部公車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw
    # 南大區間車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw
    def get_nanda_data(self):
        url = "https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw"
        res_text = cached_request.get(url)

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
