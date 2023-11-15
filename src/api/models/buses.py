import json
import re

from src.utils import cached_request


class Buses:
    # 校本部公車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw
    # 南大區間車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw
    def __init__(self) -> None:
        self.res_text = ""

    def _parse_campus_info(self, variable_string: str):
        regex_pattern = r"const " + variable_string + " = (\{.*?\})"
        data = re.search(regex_pattern, self.res_text, re.S)
        if data is not None:
            data = data.group(1)
        else:
            return None
        data = data.replace("'", "|")
        data = data.replace('"', '\\"')
        data = data.replace("|", '"')
        data = data.replace("\n", "")
        data = data.replace("direction", '"direction"')
        data = data.replace("duration", '"duration"')
        data = data.replace("route", '"route"', 1)
        data = data.replace("routeEN", '"routeEN"')
        data = json.loads(data)
        return data

    def _parse_bus_schedule(self, variable_string: str):
        regex_pattern = r"const " + variable_string + " = (\[.*?\])"
        data = re.search(regex_pattern, self.res_text, re.S)
        if data is not None:
            data = data.group(1)
        else:
            return None
        data = data.replace("'", '"')
        data = data.replace("\n", "")
        data = data.replace("time", '"time"')
        data = data.replace("description", '"description"')
        data = data.replace("depStop", '"depStop"')
        data = data.replace("line", '"line"')
        data = data.replace(",    ]", "]")
        data = data.replace(",  ]", "]")
        data = json.loads(data)
        return data

    def get_main_data(self) -> dict:
        url = "https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw"
        self.res_text = cached_request.get(url)

        # 往台積館資訊
        toward_tsmc_building_info = self._parse_campus_info("towardTSMCBuildingInfo")

        # 往台積館時刻表(平日)
        weekday_bus_schedule_toward_tsmc_building = self._parse_bus_schedule(
            "weekdayBusScheduleTowardTSMCBuilding"
        )

        # 往台積館時刻表(假日)
        weekend_bus_schedule_toward_tsmc_building = self._parse_bus_schedule(
            "weekendBusScheduleTowardTSMCBuilding"
        )

        # 往校門口資訊
        toward_main_gate_info = self._parse_campus_info("towardMainGateInfo")

        # 往校門口時刻表(平日)
        weekday_bus_schedule_toward_main_gate = self._parse_bus_schedule(
            "weekdayBusScheduleTowardMainGate"
        )

        # 往校門口時刻表(假日)
        weekend_bus_schedule_toward_main_gate = self._parse_bus_schedule(
            "weekendBusScheduleTowardMainGate"
        )

        # 輸出 json 檔案
        nanda_dataset = {
            "toward_TSMC_building_info": toward_tsmc_building_info,
            "weekday_bus_schedule_toward_TSMC_building": weekday_bus_schedule_toward_tsmc_building,
            "weekend_bus_schedule_toward_TSMC_building": weekend_bus_schedule_toward_tsmc_building,
            "toward_main_gate_info": toward_main_gate_info,
            "weekday_bus_schedule_toward_main_gate": weekday_bus_schedule_toward_main_gate,
            "weekend_bus_schedule_toward_main_gate": weekend_bus_schedule_toward_main_gate,
        }

        return nanda_dataset

    def get_nanda_data(self) -> dict:
        url = "https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw"
        self.res_text = cached_request.get(url)

        # 往南大校區資訊
        toward_south_campus_info = self._parse_campus_info("towardSouthCampusInfo")

        # 往南大校區時刻表(平日)
        weekday_bus_schedule_toward_south_campus = self._parse_bus_schedule(
            "weekdayBusScheduleTowardSouthCampus"
        )

        # 往南大校區時刻表(假日)
        weekend_bus_schedule_toward_south_campus = self._parse_bus_schedule(
            "weekendBusScheduleTowardSouthCampus"
        )

        # 往校本部資訊
        toward_main_campus_info = self._parse_campus_info("towardMainCampusInfo")

        # 往校本部時刻表(平日)
        weekday_bus_schedule_toward_main_campus = self._parse_bus_schedule(
            "weekdayBusScheduleTowardMainCampus"
        )

        # 往校本部時刻表(假日)
        weekend_bus_schedule_toward_main_campus = self._parse_bus_schedule(
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
