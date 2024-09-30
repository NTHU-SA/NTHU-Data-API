import datetime
import json
import re
from concurrent.futures import ThreadPoolExecutor
from functools import reduce
from itertools import product
from typing import Literal

import pandas as pd
from cachetools import TTLCache, cached

from src.api import schemas
from src.utils import cached_requests

# 務必保持之後的程式碼中，BUS_TYPE、BUS_DAY、BUS_DIRECTION 的順序一致，因為 BusType、BusDay 具有 all 這個選項
# 之後合併要先處理完 BusDirection 的部份才會合併到 all
BUS_TYPE = [_.value for _ in schemas.buses.BusType]
BUS_TYPE_WITHOUT_ALL = [_.value for _ in schemas.buses.BusType][
    1:
]  # 預設第一個為 all，並將其移除
BUS_DAY = [_.value for _ in schemas.buses.BusDay]
BUS_DAY_WITHOUT_ALL = [_.value for _ in schemas.buses.BusDay][
    1:
]  # 預設第一個為 all，並將其移除
BUS_DIRECTION = [_.value for _ in schemas.buses.BusDirection]

schedule_index = pd.MultiIndex.from_product([BUS_TYPE, BUS_DAY, BUS_DIRECTION])


def after_specific_time(
    target_list,
    time,
    time_path: list = None,
) -> list:
    hour, minute = map(int, time.split(":"))

    res = []

    for bus in target_list:
        bus_hour, bus_minute = map(int, reduce(dict.get, time_path, bus).split(":"))

        if bus_hour > hour or (bus_hour == hour and bus_minute >= minute):
            res.append(bus)

    return res


def sort_by_time(target, time_path: list = None) -> None:
    target.sort(
        key=lambda x: datetime.datetime.strptime(
            reduce(dict.get, time_path, x), "%H:%M"
        )
    )


def gen_all_field(target_dataframe: pd.DataFrame, time_path: list) -> None:
    for scope, direction in product(BUS_TYPE_WITHOUT_ALL, BUS_DIRECTION):
        target_dataframe.loc[(scope, "all", direction), "data"] = (
            target_dataframe.loc[(scope, "weekday", direction), "data"]
            + target_dataframe.loc[(scope, "weekend", direction), "data"]
        )

    for day, direction in product(BUS_DAY, BUS_DIRECTION):
        target_dataframe.loc[("all", day, direction), "data"] = (
            target_dataframe.loc[("main", day, direction), "data"]
            + target_dataframe.loc[("nanda", day, direction), "data"]
        )

    for scope, day, direction in product(BUS_TYPE, BUS_DAY, BUS_DIRECTION):
        sort_by_time(
            target_dataframe.loc[(scope, day, direction), "data"],
            time_path,
        )


class Stop:
    def __init__(self, name: str, name_en: str, latitude: str, longitude: str) -> None:
        self.name = name
        self.name_en = name_en
        self.latitude = latitude
        self.longitude = longitude
        # self.stopped_bus 共有 18 個 entries 需要被初始賦值為空 list，避免後續對 nan 做 append() 導致錯誤
        # data init 不能用 [[]] * 18，因為這樣會讓所有 entries 共用同一個 list（shallow copy）
        self.stopped_bus = pd.DataFrame(
            data={"data": [[] for _ in range(len(schedule_index))]},
            index=schedule_index,
        )


M1 = Stop("北校門口", "North Main Gate", "24.79589", "120.99633")
M2 = Stop("綜二館", "General Building II", "24.794176", "120.99376")
M3 = Stop("楓林小徑", "Maple Path", "24.791388889", "120.991388889")
M4 = Stop("人社院/生科館", "CHSS/CLS Building", "24.79", "120.990277778")
M5 = Stop("台積館", "TSMC Building", "24.78695", "120.9884")
M6 = Stop(
    "奕園停車場", "Yi Pavilion Parking Lot", "24.788284441920126", "120.99246131713849"
)
M7 = Stop("南門停車場", "South Gate Parking Lot", "24.7859395", "120.9901396")
S1 = Stop(
    "南大校區校門口右側(食品路校牆邊)",
    "The right side of NandaCampus front gate(Shipin Road)",
    "24.79438267696105",
    "120.965382976675",
)
stops = {"M1": M1, "M2": M2, "M3": M3, "M4": M4, "M5": M5, "M6": M6, "M7": M7, "S1": S1}

# 清大路網圖 (單位：分鐘)
#                        M4
#     1      1     2/         \2    15
# M1 --- M2 --- M3              M5 ---- S1
#                 1\          /1
#                   M6 --- M7
#                       2


class Route:
    def __init__(self, *arg) -> None:
        self.stops: list[Stop] = list(arg)
        self._delta_time_table = {
            M1: {M2: 1},
            M2: {M1: 1, M3: 1, M4: 3},
            M3: {M2: 1, M4: 2, M6: 1},
            M4: {M2: 3, M3: 2, M5: 2},
            M5: {M4: 2, M7: 1, S1: 15},
            M6: {M3: 1, M7: 2},
            M7: {M5: 1, M6: 2},
            S1: {M5: 15},
        }

    def gen_accumulated_time(self) -> list:
        res = [0]
        for i in range(0, len(self.stops) - 1):
            res.append(
                res[i] + self._delta_time_table[self.stops[i]][self.stops[i + 1]]
            )
        return res


red_M1_M5 = Route(M1, M2, M3, M4, M5)  # 紅線 北校門 往 台積館
red_M5_M1 = Route(M5, M7, M6, M3, M2, M1)  # 紅線 台積館 往 北校門
red_M2_M5 = Route(M2, M3, M4, M5)  # 紅線 綜二館 往 台積館
red_M5_M2 = Route(M5, M7, M6, M3, M2)  # 紅線 台積館 往 綜二館

green_M1_M5 = Route(M1, M2, M3, M6, M7, M5)  # 綠線 北校門 往 台積館
green_M5_M1 = Route(M5, M4, M3, M2, M1)  # 綠線 台積館 往 北校門
green_M2_M5 = Route(M2, M3, M6, M7, M5)  # 綠線 綜二館 往 台積館
green_M5_M2 = Route(M5, M4, M3, M2)  # 綠線 台積館 往 綜二館

nanda_M1_S1 = Route(
    M1, M2, M4, M5, S1
)  # 校區區間車 南大校區校門口右側(食品路校牆邊) 往 北校門
nanda_S1_M1 = Route(
    S1, M5, M4, M2, M1
)  # 校區區間車 北校門 往 南大校區校門口右側(食品路校牆邊)


class Buses:
    # 校本部公車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw
    # 南大區間車
    # https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw
    def __init__(self) -> None:
        self._res_text = ""
        self._start_from_gen_2_bus_info = []

        self._info_index = pd.MultiIndex.from_product(
            [BUS_TYPE_WITHOUT_ALL, BUS_DIRECTION]
        )
        self.raw_schedule_data = pd.DataFrame(index=schedule_index, columns=["data"])
        self.detailed_schedule_data = pd.DataFrame(
            index=schedule_index, columns=["data"]
        )
        self.info_data = pd.DataFrame(index=self._info_index, columns=["data"])

    def _parse_campus_info(self, variable_string: str):
        regex_pattern = r"const " + variable_string + r" = (\{.*?\})"
        data = re.search(regex_pattern, self._res_text, re.S)
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

        return [data]  # turn to list to store in DataFrame

    def _parse_bus_schedule(self, variable_string: str):
        regex_pattern = r"const " + variable_string + r" = (\[.*?\])"
        data = re.search(regex_pattern, self._res_text, re.S)
        if data is not None:
            data = data.group(1)
        else:
            return None
        data = data.replace("'", '"')
        data = data.replace("\n", "")
        data = data.replace("time", '"time"')
        data = data.replace("description", '"description"')
        data = data.replace("depStop", '"dep_stop"')
        data = data.replace("line", '"line"')
        data = re.sub(r",[ ]+?\]", "]", data)  # remove trailing comma
        data = json.loads(data)

        data = [i for i in data if i["time"] != ""]  # remove empty time
        for i in data:
            i["route"] = "校園公車" if "line" in data[0] else "南大區間車"

        return data

    def transform_toward_name(
        self, route: Literal["main", "nanda"], direction: Literal["up", "down"]
    ) -> str:
        trans_list = {
            ("main", "up"): "TSMCBuilding",
            ("main", "down"): "MainGate",
            ("nanda", "up"): "SouthCampus",
            ("nanda", "down"): "MainCampus",
        }

        return trans_list[(route, direction)]

    @cached(TTLCache(maxsize=8, ttl=60 * 60 * 24))
    def get_all_data(self):
        main_url = "https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw"
        nanda_url = "https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw"

        with ThreadPoolExecutor(max_workers=2) as executor:
            main_text, nanda_text = executor.map(
                lambda url: cached_requests.get(url, update=True, auto_headers=True)[0],
                [main_url, nanda_url],
            )
        self._res_text = main_text + nanda_text

        # schedule data
        for scope, day, direction in product(
            BUS_TYPE_WITHOUT_ALL, BUS_DAY, BUS_DIRECTION
        ):
            self.raw_schedule_data.loc[(scope, day, direction), "data"] = (
                self._parse_bus_schedule(
                    f"{day}BusScheduleToward{self.transform_toward_name(scope, direction)}"
                )
            )

        # info data
        for scope, direction in product(BUS_TYPE_WITHOUT_ALL, BUS_DIRECTION):
            self.info_data.loc[(scope, direction), "data"] = self._parse_campus_info(
                f"toward{self.transform_toward_name(scope, direction)}Info"
            )

        gen_all_field(self.raw_schedule_data, ["time"])

    def get_main_data(self) -> dict:
        # 輸出 json 檔案
        main_dataset = {
            "toward_TSMC_building_info": self.info_data.loc[("main", "up"), "data"][0],
            "weekday_bus_schedule_toward_TSMC_building": self.raw_schedule_data.loc[
                ("main", "weekday", "up"), "data"
            ],
            "weekend_bus_schedule_toward_TSMC_building": self.raw_schedule_data.loc[
                ("main", "weekend", "up"), "data"
            ],
            "toward_main_gate_info": self.info_data.loc[("main", "down"), "data"][0],
            "weekday_bus_schedule_toward_main_gate": self.raw_schedule_data.loc[
                ("main", "weekday", "down"), "data"
            ],
            "weekend_bus_schedule_toward_main_gate": self.raw_schedule_data.loc[
                ("main", "weekend", "down"), "data"
            ],
        }

        return main_dataset

    def get_nanda_data(self) -> dict:
        # 輸出 json 檔案
        nanda_dataset = {
            "toward_south_campus_info": self.info_data.loc[("nanda", "up"), "data"][0],
            "weekday_bus_schedule_toward_south_campus": self.raw_schedule_data.loc[
                ("nanda", "weekday", "up"), "data"
            ],
            "weekend_bus_schedule_toward_south_campus": self.raw_schedule_data.loc[
                ("nanda", "weekend", "up"), "data"
            ],
            "toward_main_campus_info": self.info_data.loc[("nanda", "down"), "data"][0],
            "weekday_bus_schedule_toward_main_campus": self.raw_schedule_data.loc[
                ("nanda", "weekday", "down"), "data"
            ],
            "weekend_bus_schedule_toward_main_campus": self.raw_schedule_data.loc[
                ("nanda", "weekend", "down"), "data"
            ],
        }

        return nanda_dataset

    def _reset_stop_data(self):
        for stop in stops.values():
            stop.stopped_bus = pd.DataFrame(
                data={"data": [[] for _ in range(len(schedule_index))]},
                index=schedule_index,
            )

    # 更新資料，並清除 _start_from_gen_2_bus_info
    def _update_data(self):
        self.get_all_data()
        self._start_from_gen_2_bus_info = []

    def _add_on_time(self, start_time: str, time_delta: int) -> str:
        st = datetime.datetime.strptime(start_time, "%H:%M")
        st = st + datetime.timedelta(minutes=time_delta)
        return str(st.strftime("%H:%M"))

    # 用字串尋找對應的 Stop 物件
    def _find_stop_from_str(self, stop_str: str) -> Stop:
        for stop in stops.values():
            if stop.name == stop_str:
                return stop

    def _route_selector(
        self, dep_stop: str, line: str, from_gen_2: bool = False
    ) -> Route:
        # 清理資料，爬蟲抓下來的資料有些會多空格
        (dep_stop, line) = map(str.strip, [dep_stop, line])

        stops_lines_map = {
            ("台積館", "red", True): red_M5_M2,
            ("台積館", "red", False): red_M5_M1,
            ("台積館", "green", True): green_M5_M2,
            ("台積館", "green", False): green_M5_M1,
            ("校門", "red"): red_M1_M5,
            ("綜二", "red"): red_M2_M5,
            ("校門", "green"): green_M1_M5,
            ("綜二", "green"): green_M2_M5,
        }

        key = (
            (dep_stop, line) if "台積" not in dep_stop else (dep_stop, line, from_gen_2)
        )
        return stops_lines_map.get(key, None)

    def _gen_detailed_bus_schedule(
        self,
        bus_schedule: list,
        *,
        scope: Literal["main", "nanda"] = "main",
        day: Literal["weekday", "weekend"] = "weekday",
        direction: Literal["up", "down"] = "up",
    ) -> list:
        res = []
        for bus in bus_schedule:
            temp_bus = {"dep_info": bus, "stops_time": []}

            this_route = None
            # 校本部公車
            if scope == "main":
                # 判斷路線
                dep_stop = bus["dep_stop"]
                line = bus["line"]

                # 判斷是否上山時從綜二館出發，將影響下山的終點站
                # 有 0 的情況是因為資料中有些時間是 8:00 這種格式
                dep_from_gen_2 = (
                    bus["time"] + line in self._start_from_gen_2_bus_info
                    or "0" + bus["time"] + line in self._start_from_gen_2_bus_info
                )

                this_route = self._route_selector(dep_stop, line, dep_from_gen_2)

                # 如果從綜二出發，紀錄該班資訊
                if dep_stop.count("綜二") > 0:
                    self._start_from_gen_2_bus_info.append(
                        str(self._add_on_time(bus["time"], 7) + line)
                    )
            # 南大區間車
            elif scope == "nanda":
                # 判斷路線
                if direction == "up":
                    this_route = nanda_M1_S1
                elif direction == "down":
                    this_route = nanda_S1_M1

            for index, stop in enumerate(this_route.stops):
                arrive_time = self._add_on_time(
                    bus["time"],
                    this_route.gen_accumulated_time()[index],
                )

                # 處理各站牌資訊
                self._find_stop_from_str(stop.name).stopped_bus.loc[
                    (scope, day, direction), "data"
                ].append({"bus_info": bus, "arrive_time": arrive_time})

                temp_bus["stops_time"].append(
                    {"stop_name": stop.name, "time": arrive_time}
                )

            res.append(temp_bus)

        return res

    @cached(TTLCache(maxsize=8, ttl=60 * 60 * 24))
    def gen_bus_detailed_schedule_and_update_stops_data(self):
        """
        若使用這個 function，同時也會呼叫 get_all_data()，因此不需要再另外呼叫 get_all_data()。
        """
        self._reset_stop_data()

        for scope, day, direction in product(
            BUS_TYPE_WITHOUT_ALL, BUS_DAY_WITHOUT_ALL, BUS_DIRECTION
        ):
            self._update_data()
            self.detailed_schedule_data.loc[(scope, day, direction), "data"] = (
                self._gen_detailed_bus_schedule(
                    self.raw_schedule_data.loc[(scope, day, direction), "data"],
                    scope=scope,
                    day=day,
                    direction=direction,
                )
            )

        gen_all_field(self.detailed_schedule_data, ["dep_info", "time"])
        for stop in stops.values():
            gen_all_field(stop.stopped_bus, ["arrive_time"])

    def gen_bus_stops_info(self) -> list:
        res = []
        for stop in stops.values():
            res.append(
                {
                    "stop_name": stop.name,
                    "stop_name_en": stop.name_en,
                    "latitude": stop.latitude,
                    "longitude": stop.longitude,
                }
            )

        return res
