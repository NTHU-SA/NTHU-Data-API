from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import reduce
from itertools import product
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
import requests

from src.api import schemas

# ---------------------------------------------------------------------------
# 常數與全域變數設定
# ---------------------------------------------------------------------------
# 保持後續程式中 BUS_TYPE, BUS_DAY, BUS_DIRECTION 的順序一致，因 BusType、BusDay 具有 all 選項
BUS_TYPE: List[str] = [bus_type.value for bus_type in schemas.buses.BusType]
BUS_TYPE_WITHOUT_ALL: List[str] = BUS_TYPE[1:]  # 第一個為 all，故移除
BUS_DAY: List[str] = [bus_day.value for bus_day in schemas.buses.BusDay]
BUS_DAY_WITHOUT_ALL: List[str] = BUS_DAY[1:]
BUS_DIRECTION: List[str] = [bus_dir.value for bus_dir in schemas.buses.BusDirection]

schedule_index = pd.MultiIndex.from_product([BUS_TYPE, BUS_DAY, BUS_DIRECTION])


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def get_nested_value(data: dict, keys: List[str]) -> Any:
    """依照 keys 依序取出巢狀字典中的值，keys 為取值路徑。"""
    return reduce(dict.get, keys, data)


def after_specific_time(
    target_list: List[dict], time_str: str, time_path: Optional[List[str]] = None
) -> List[dict]:
    """回傳在特定時間點之後的資料。

    Args:
        target_list: 包含時間字串的字典列表
        time_str: 比較用時間字串，格式 'HH:MM'
        time_path: 指定在字典中取得時間字串的 key 路徑，若為 None 則預設直接使用該字典

    Returns:
        過濾後的列表
    """
    ref_hour, ref_minute = map(int, time_str.split(":"))
    res = []
    for bus in target_list:
        bus_time = get_nested_value(bus, time_path) if time_path else bus
        bus_hour, bus_minute = map(int, bus_time.split(":"))
        if bus_hour > ref_hour or (bus_hour == ref_hour and bus_minute >= ref_minute):
            res.append(bus)
    return res


def sort_by_time(target: List[dict], time_path: Optional[List[str]] = None) -> None:
    """依照時間排序 target 列表，時間字串格式必須為 '%H:%M'。"""
    target.sort(
        key=lambda x: datetime.strptime(
            get_nested_value(x, time_path) if time_path else x, "%H:%M"
        )
    )


def gen_all_field(target_dataframe: pd.DataFrame, time_path: List[str]) -> None:
    """依照產品的組合，將資料合併到 'all' 欄位，並依照時間排序。"""
    # 先針對 BUS_TYPE_WITHOUT_ALL 合併 weekday 與 weekend
    for scope, direction in product(BUS_TYPE_WITHOUT_ALL, BUS_DIRECTION):
        weekday_data = target_dataframe.loc[(scope, "weekday", direction), "data"]
        weekend_data = target_dataframe.loc[(scope, "weekend", direction), "data"]
        target_dataframe.loc[(scope, "all", direction), "data"] = (
            weekday_data + weekend_data
        )

    # 合併不同 BusType 的資料
    for day, direction in product(BUS_DAY, BUS_DIRECTION):
        main_data = target_dataframe.loc[("main", day, direction), "data"]
        nanda_data = target_dataframe.loc[("nanda", day, direction), "data"]
        target_dataframe.loc[("all", day, direction), "data"] = main_data + nanda_data

    # 最後對所有資料依時間排序
    for scope, day, direction in product(BUS_TYPE, BUS_DAY, BUS_DIRECTION):
        sort_by_time(target_dataframe.loc[(scope, day, direction), "data"], time_path)


# ---------------------------------------------------------------------------
# 資料結構定義
# ---------------------------------------------------------------------------
@dataclass(unsafe_hash=True)
class Stop:
    name: str
    name_en: str
    latitude: str
    longitude: str
    # 使用 field(init=False) 在初始化後設定 stopped_bus
    stopped_bus: pd.DataFrame = field(init=False, compare=False, hash=False)

    def __post_init__(self):
        self.stopped_bus = pd.DataFrame(
            {"data": [[] for _ in range(len(schedule_index))]},
            index=schedule_index,
        )


@dataclass
class Route:
    stops: List[Stop]
    # 內部的站間時間對照表
    _delta_time_table: Dict[Stop, Dict[Stop, int]] = field(
        default_factory=dict, init=False
    )

    def __post_init__(self):
        # 預設的路線時間資料
        # 請注意：此處以全域定義的 Stop 物件作 key
        self._delta_time_table = {
            stops["M1"]: {stops["M2"]: 1},
            stops["M2"]: {stops["M1"]: 1, stops["M3"]: 1, stops["M4"]: 3},
            stops["M3"]: {stops["M2"]: 1, stops["M4"]: 2, stops["M6"]: 1},
            stops["M4"]: {stops["M2"]: 3, stops["M3"]: 2, stops["M5"]: 2},
            stops["M5"]: {stops["M4"]: 2, stops["M7"]: 1, stops["S1"]: 15},
            stops["M6"]: {stops["M3"]: 1, stops["M7"]: 2},
            stops["M7"]: {stops["M5"]: 1, stops["M6"]: 2},
            stops["S1"]: {stops["M5"]: 15},
        }

    def gen_accumulated_time(self) -> List[int]:
        """計算每站所累積的時間，第一站時間為 0。"""
        acc_times = [0]
        for i in range(len(self.stops) - 1):
            acc_times.append(
                acc_times[i] + self._delta_time_table[self.stops[i]][self.stops[i + 1]]
            )
        return acc_times


# ---------------------------------------------------------------------------
# Stop 物件初始化
# ---------------------------------------------------------------------------
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
stops: Dict[str, Stop] = {
    "M1": M1,
    "M2": M2,
    "M3": M3,
    "M4": M4,
    "M5": M5,
    "M6": M6,
    "M7": M7,
    "S1": S1,
}
stop_name_mapping: Dict[str, Stop] = {stop.name: stop for stop in stops.values()}

# 清大路網圖 (單位：分鐘)
#                        M4
#     1      1     2/         \2    15
# M1 --- M2 --- M3              M5 ---- S1
#                 1\          /1
#                   M6 --- M7

# ---------------------------------------------------------------------------
# 路線定義
# ---------------------------------------------------------------------------
# 紅線
red_M1_M5 = Route([M1, M2, M3, M4, M5])  # 北校門往台積館
red_M5_M1 = Route([M5, M7, M6, M3, M2, M1])  # 台積館往北校門
red_M2_M5 = Route([M2, M3, M4, M5])  # 綜二館往台積館
red_M5_M2 = Route([M5, M7, M6, M3, M2])  # 台積館往綜二館

# 綠線
green_M1_M5 = Route([M1, M2, M3, M6, M7, M5])  # 北校門往台積館
green_M5_M1 = Route([M5, M4, M3, M2, M1])  # 台積館往北校門
green_M2_M5 = Route([M2, M3, M6, M7, M5])  # 綜二館往台積館
green_M5_M2 = Route([M5, M4, M3, M2])  # 台積館往綜二館

# 校區區間車
nanda_M1_S1 = Route([M1, M2, M4, M5, S1])  # 南大校區校門口右側往北校門
nanda_S1_M1 = Route([S1, M5, M4, M2, M1])  # 北校門往南大校區校門口右側

# ---------------------------------------------------------------------------
# Buses 類別
# ---------------------------------------------------------------------------


class Buses:
    """
    校園公車時刻表

    - 校本部公車
    https://affairs.site.nthu.edu.tw/p/412-1165-20978.php?Lang=zh-tw
    - 南大區間車
    https://affairs.site.nthu.edu.tw/p/412-1165-20979.php?Lang=zh-tw

    資料來源：https://nthu-data-json.pages.dev/buses.json
    """

    def __init__(self) -> None:
        self._res_json: dict = {}
        self._start_from_gen_2_bus_info: List[str] = []

        info_index = pd.MultiIndex.from_product([BUS_TYPE_WITHOUT_ALL, BUS_DIRECTION])
        self.raw_schedule_data = pd.DataFrame(
            {"data": [[] for _ in range(len(schedule_index))]}, index=schedule_index
        )
        self.detailed_schedule_data = pd.DataFrame(
            {"data": [[] for _ in range(len(schedule_index))]}, index=schedule_index
        )
        self.info_data = pd.DataFrame(
            {"data": [[] for _ in range(len(info_index))]}, index=info_index
        )

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

    def get_all_data(self) -> None:
        json_url = "https://nthu-data-json.pages.dev/buses.json"
        try:
            response = requests.get(json_url)
            response.raise_for_status()
            self._res_json = response.json()
        except requests.RequestException as e:
            print(f"Error fetching data from {json_url}: {e}")
            return

        # 取得 schedule data
        for scope, day, direction in product(
            BUS_TYPE_WITHOUT_ALL, BUS_DAY, BUS_DIRECTION
        ):
            schedule_key = (
                f"{day}BusScheduleToward{self.transform_toward_name(scope, direction)}"
            )
            schedule_data = self._res_json.get(schedule_key, [])
            self.raw_schedule_data.loc[(scope, day, direction), "data"] = schedule_data

        # 取得 info data
        for scope, direction in product(BUS_TYPE_WITHOUT_ALL, BUS_DIRECTION):
            info_key = f"toward{self.transform_toward_name(scope, direction)}Info"
            info_data = self._res_json.get(info_key, {})
            self.info_data.loc[(scope, direction), "data"] = [info_data]

        gen_all_field(self.raw_schedule_data, ["time"])

    def get_main_data(self) -> dict:
        return {
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

    def get_nanda_data(self) -> dict:
        return {
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

    def _reset_stop_data(self) -> None:
        # 重新初始化所有 Stop 的 stopped_bus DataFrame
        for stop in stops.values():
            stop.stopped_bus = pd.DataFrame(
                {"data": [[] for _ in range(len(schedule_index))]},
                index=schedule_index,
            )

    def _update_data(self) -> None:
        self.get_all_data()
        self._start_from_gen_2_bus_info.clear()

    def _add_on_time(self, start_time: str, time_delta: int) -> str:
        st = datetime.strptime(start_time, "%H:%M") + timedelta(minutes=time_delta)
        return st.strftime("%H:%M")

    def _find_stop_from_str(self, stop_str: str) -> Optional[Stop]:
        return stop_name_mapping.get(stop_str)

    def _route_selector(
        self, dep_stop: str, line: str, from_gen_2: bool = False
    ) -> Optional[Route]:
        dep_stop, line = dep_stop.strip(), line.strip()
        stops_lines_map: Dict[tuple, Route] = {
            ("台積館", "red", True): red_M5_M2,
            ("台積館", "red", False): red_M5_M1,
            ("台積館", "green", True): green_M5_M2,
            ("台積館", "green", False): green_M5_M1,
            ("校門", "red"): red_M1_M5,
            ("綜二", "red"): red_M2_M5,
            ("校門", "green"): green_M1_M5,
            ("綜二", "green"): green_M5_M2,
        }
        key = (
            (dep_stop, line) if "台積" not in dep_stop else (dep_stop, line, from_gen_2)
        )
        return stops_lines_map.get(key)

    def _gen_detailed_bus_schedule(
        self,
        bus_schedule: List[dict],
        *,
        scope: Literal["main", "nanda"] = "main",
        day: Literal["weekday", "weekend"] = "weekday",
        direction: Literal["up", "down"] = "up",
    ) -> List[dict]:
        res = []
        for bus in bus_schedule:
            temp_bus = {"dep_info": bus, "stops_time": []}
            this_route: Optional[Route] = None

            if scope == "main":
                dep_stop = bus.get("dep_stop", "")
                line = bus.get("line", "")
                # 檢查是否從綜二出發（注意處理資料中可能缺少前導 0 的情形）
                dep_from_gen_2 = (
                    bus["time"] + line in self._start_from_gen_2_bus_info
                ) or ("0" + bus["time"] + line in self._start_from_gen_2_bus_info)
                this_route = self._route_selector(dep_stop, line, dep_from_gen_2)
                if "綜二" in dep_stop:
                    self._start_from_gen_2_bus_info.append(
                        self._add_on_time(bus["time"], 7) + line
                    )
            elif scope == "nanda":
                this_route = nanda_M1_S1 if direction == "up" else nanda_S1_M1

            if this_route:
                acc_times = this_route.gen_accumulated_time()
                for idx, stop in enumerate(this_route.stops):
                    arrive_time = self._add_on_time(bus["time"], acc_times[idx])
                    stop_obj = self._find_stop_from_str(stop.name)
                    if stop_obj:
                        stop_obj.stopped_bus.loc[
                            (scope, day, direction), "data"
                        ].append(
                            {
                                "bus_info": bus,
                                "arrive_time": arrive_time,
                            }
                        )
                    temp_bus["stops_time"].append(
                        {
                            "stop_name": stop.name,
                            "time": arrive_time,
                        }
                    )
            res.append(temp_bus)
        return res

    def gen_bus_detailed_schedule_and_update_stops_data(self) -> None:
        """
        此函式會呼叫 get_all_data() 更新資料，並同時更新 detailed_schedule_data 與各 Stop 的 stopped_bus。
        """
        self._reset_stop_data()
        self._update_data()

        for scope, day, direction in product(
            BUS_TYPE_WITHOUT_ALL, BUS_DAY_WITHOUT_ALL, BUS_DIRECTION
        ):
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

    def gen_bus_stops_info(self) -> List[dict]:
        return [
            {
                "stop_name": stop.name,
                "stop_name_en": stop.name_en,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
            }
            for stop in stops.values()
        ]
