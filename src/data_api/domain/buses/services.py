"""
Buses domain service.

Contains all business logic for bus data processing, caching, and retrieval.
This is extracted from the original models/buses.py and cleaned up.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import reduce
from itertools import product
from typing import Any, Literal, Optional

import pandas as pd

from data_api.core import constants
from data_api.data.manager import nthudata
from data_api.domain.buses import enums, models

# Constants
DATA_TTL_HOURS = constants.DATA_TTL_HOURS

# Type lists for iteration
BUS_ROUTE_TYPE = [t.value for t in enums.BusRouteType]
BUS_ROUTE_TYPE_WITHOUT_ALL = BUS_ROUTE_TYPE[1:]  # Exclude 'all'
BUS_DAY = [d.value for d in enums.BusDay]
BUS_DAY_WITHOUT_ALL = BUS_DAY[1:]  # Exclude 'all'
BUS_DIRECTION = [d.value for d in enums.BusDirection]

schedule_index = pd.MultiIndex.from_product([BUS_ROUTE_TYPE, BUS_DAY, BUS_DIRECTION])


# Helper functions
def get_nested_value(data: dict, keys: list[str]) -> Any:
    """Get value from nested dict using key path."""
    return reduce(dict.get, keys, data)


def after_specific_time(
    target_list: list[dict], time_str: str, time_path: Optional[list[str]] = None
) -> list[dict]:
    """Filter list to keep only items after specified time."""
    ref_hour, ref_minute = map(int, time_str.split(":"))
    filtered_list = []
    for item in target_list:
        item_time_str = get_nested_value(item, time_path) if time_path else item
        item_hour, item_minute = map(int, item_time_str.split(":"))
        if item_hour > ref_hour or (
            item_hour == ref_hour and item_minute >= ref_minute
        ):
            filtered_list.append(item)
    return filtered_list


def sort_by_time(target: list[dict], time_path: Optional[list[str]] = None) -> None:
    """Sort dict list by time."""
    target.sort(
        key=lambda x: datetime.strptime(
            get_nested_value(x, time_path) if time_path else x, "%H:%M"
        )
    )


def gen_the_all_field(target_dataframe: pd.DataFrame, time_path: list[str]) -> None:
    """Generate 'all' field by merging data and sorting by time."""
    # Merge weekday and weekend for each route type
    for route_type, direction in product(BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DIRECTION):
        weekday_data = target_dataframe.loc[(route_type, "weekday", direction), "data"]
        weekend_data = target_dataframe.loc[(route_type, "weekend", direction), "data"]
        target_dataframe.loc[(route_type, "all", direction), "data"] = (
            weekday_data + weekend_data
        )

    # Merge different route types
    for day, direction in product(BUS_DAY, BUS_DIRECTION):
        main_data = target_dataframe.loc[("main", day, direction), "data"]
        nanda_data = target_dataframe.loc[("nanda", day, direction), "data"]
        target_dataframe.loc[("all", day, direction), "data"] = main_data + nanda_data

    # Sort all data by time
    for route_type, day, direction in product(BUS_ROUTE_TYPE, BUS_DAY, BUS_DIRECTION):
        sort_by_time(
            target_dataframe.loc[(route_type, day, direction), "data"], time_path
        )


# Stop instances
M1 = models.Stop("北校門口", "North Main Gate", "24.79589", "120.99633")
M2 = models.Stop("綜二館", "General Building II", "24.794176", "120.99376")
M3 = models.Stop("楓林小徑", "Maple Path", "24.791388889", "120.991388889")
M4 = models.Stop("人社院&生科館", "CHSS&CLS Building", "24.79", "120.990277778")
M5 = models.Stop("台積館", "TSMC Building", "24.78695", "120.9884")
M6 = models.Stop(
    "奕園停車場", "Yi Pavilion Parking Lot", "24.788284441920126", "120.99246131713849"
)
M7 = models.Stop("南門停車場", "South Gate Parking Lot", "24.7859395", "120.9901396")
S1 = models.Stop(
    "南大校區校門口右側(食品路校牆邊)",
    "The right side of NandaCampus front gate(Shipin Road)",
    "24.79438267696105",
    "120.965382976675",
)

stops: dict[str, models.Stop] = {
    "M1": M1,
    "M2": M2,
    "M3": M3,
    "M4": M4,
    "M5": M5,
    "M6": M6,
    "M7": M7,
    "S1": S1,
}

stop_name_mapping: dict[str, models.Stop] = {stop.name: stop for stop in stops.values()}


# Initialize stop data structures
def _init_stop_data():
    """Initialize stopped_bus_data for all stops."""
    for stop in stops.values():
        stop.stopped_bus_data = {}
        for route_type, day, direction in product(BUS_ROUTE_TYPE, BUS_DAY, BUS_DIRECTION):
            stop.stopped_bus_data[(route_type, day, direction)] = []


_init_stop_data()


# Route definitions
red_M1_M5 = models.Route([M1, M2, M3, M4, M5])
red_M5_M1 = models.Route([M5, M7, M6, M2, M1])
red_M2_M5 = models.Route([M2, M3, M4, M5])
red_M5_M2 = models.Route([M5, M7, M6, M2])

green_M1_M5 = models.Route([M1, M2, M3, M6, M7, M5])
green_M5_M1 = models.Route([M5, M4, M2, M1])
green_M2_M5 = models.Route([M2, M3, M6, M7, M5])
green_M5_M2 = models.Route([M5, M4, M2])

nanda_M1_S1 = models.Route([M1, M2, M4, M5, S1])
nanda_S1_M1 = models.Route([S1, M5, M4, M2, M1])

# Initialize delta time tables for routes
red_M1_M5.delta_time_table = {M1: {M2: 1}, M2: {M3: 1}, M3: {M4: 2}, M4: {M5: 2}}
red_M5_M1.delta_time_table = {M5: {M7: 1}, M7: {M6: 2}, M6: {M2: 1}, M2: {M1: 1}}
red_M2_M5.delta_time_table = {M2: {M3: 1}, M3: {M4: 2}, M4: {M5: 2}}
red_M5_M2.delta_time_table = {M5: {M7: 1}, M7: {M6: 2}, M6: {M2: 1}}

green_M1_M5.delta_time_table = {M1: {M2: 1}, M2: {M3: 1}, M3: {M6: 1}, M6: {M7: 2}, M7: {M5: 1}}
green_M5_M1.delta_time_table = {M5: {M4: 2}, M4: {M2: 3}, M2: {M1: 1}}
green_M2_M5.delta_time_table = {M2: {M3: 1}, M3: {M6: 1}, M6: {M7: 2}, M7: {M5: 1}}
green_M5_M2.delta_time_table = {M5: {M4: 2}, M4: {M2: 3}}

nanda_M1_S1.delta_time_table = {M1: {M2: 1}, M2: {M4: 3}, M4: {M5: 2}, M5: {S1: 15}}
nanda_S1_M1.delta_time_table = {S1: {M5: 15}, M5: {M4: 2}, M4: {M2: 3}, M2: {M1: 1}}


class BusesService:
    """
    Bus schedule management service.
    
    Provides data fetching, processing, and query functions for campus bus schedules.
    """

    def __init__(self) -> None:
        """Initialize the buses service."""
        self.raw_schedule_data = pd.DataFrame(
            {"data": [[] for _ in range(len(schedule_index))]}, index=schedule_index
        )
        self.detailed_schedule_data = pd.DataFrame(
            {"data": [[] for _ in range(len(schedule_index))]}, index=schedule_index
        )
        self.info_data = pd.DataFrame(
            {
                "data": [
                    []
                    for _ in range(len(BUS_ROUTE_TYPE_WITHOUT_ALL) * len(BUS_DIRECTION))
                ]
            },
            index=pd.MultiIndex.from_product(
                [BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DIRECTION]
            ),
        )
        self.last_commit_hash = None
        self._res_json: dict = {}
        self._start_from_gen_2_bus_info: list[str] = []
        self._last_updated_time: Optional[float] = None

    async def update_data(self) -> None:
        """Update bus schedule data from remote source."""
        result = await nthudata.get("buses.json")
        if result is None:
            print("Warning: Could not fetch buses.json, keeping existing data")
            return

        res_commit_hash, self._res_json = result

        if self._res_json and res_commit_hash != self.last_commit_hash:
            await self._process_bus_data()
            self.last_commit_hash = res_commit_hash
        self._start_from_gen_2_bus_info.clear()

    async def _process_bus_data(self) -> None:
        """Process bus data from JSON."""
        self._populate_info_data()
        self._populate_raw_schedule_data()
        self._add_fields_to_raw_schedule_data()
        await self.gen_bus_detailed_schedule_and_update_stops_data()

    def _populate_info_data(self) -> None:
        """Populate info_data DataFrame from JSON."""
        for route_type, direction in product(BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DIRECTION):
            info_key = f"toward{self.transform_toward_name(route_type, direction)}Info"
            info_data = self._res_json.get(info_key, {})
            self.info_data.loc[(route_type, direction), "data"] = [info_data]

    def _populate_raw_schedule_data(self) -> None:
        """Populate raw_schedule_data DataFrame from JSON."""
        for route_type, day, direction in product(
            BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DAY, BUS_DIRECTION
        ):
            schedule_key = f"{day}BusScheduleToward{self.transform_toward_name(route_type, direction)}"
            schedule_data = self._res_json.get(schedule_key, [])
            self.raw_schedule_data.loc[(route_type, day, direction), "data"] = (
                schedule_data
            )
        gen_the_all_field(self.raw_schedule_data, ["time"])

    def _classify_bus_type(
        self, route_type: str, day: str, description: str
    ) -> str:
        """Classify bus type based on route, day, and description."""
        if route_type == "nanda" and "83" in description:
            return enums.BusType.route_83.value
        elif (route_type == "main" and "大" in description) or (
            route_type == "nanda" and day == "weekday"
        ):
            return enums.BusType.large_sized_bus.value
        else:
            return enums.BusType.middle_sized_bus.value

    def _add_fields_to_raw_schedule_data(self) -> None:
        """Add extra fields to raw schedule data."""
        for route_type, day, direction in product(
            BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DAY, BUS_DIRECTION
        ):
            for item in self.raw_schedule_data.loc[
                (route_type, day, direction), "data"
            ]:
                item["bus_type"] = self._classify_bus_type(
                    route_type, day, item["description"]
                )
                if route_type == "nanda":
                    item["dep_stop"] = "校門" if direction == "up" else "南大"

    def transform_toward_name(
        self, route: Literal["main", "nanda"], direction: Literal["up", "down"]
    ) -> str:
        """Transform route and direction to JSON key format."""
        trans_list = {
            ("main", "up"): "TSMCBuilding",
            ("main", "down"): "MainGate",
            ("nanda", "up"): "Nanda",
            ("nanda", "down"): "MainCampus",
        }
        return trans_list[(route, direction)]

    def get_main_data(self) -> dict:
        """Get main campus bus data."""
        return self._get_route_data("main")

    def get_nanda_data(self) -> dict:
        """Get Nanda campus bus data."""
        return self._get_route_data("nanda")

    def _get_route_data(self, route_type: Literal["main", "nanda"]) -> dict:
        """Get route data for specified type."""
        if route_type == "main":
            up_name = "TSMC_building"
            down_name = "main_gate"
        else:
            up_name = "nanda"
            down_name = "main_campus"

        return {
            f"toward_{up_name}_info": self.info_data.loc[(route_type, "up"), "data"][0],
            f"weekday_bus_schedule_toward_{up_name}": self.raw_schedule_data.loc[
                (route_type, "weekday", "up"), "data"
            ],
            f"weekend_bus_schedule_toward_{up_name}": self.raw_schedule_data.loc[
                (route_type, "weekend", "up"), "data"
            ],
            f"toward_{down_name}_info": self.info_data.loc[
                (route_type, "down"), "data"
            ][0],
            f"weekday_bus_schedule_toward_{down_name}": self.raw_schedule_data.loc[
                (route_type, "weekday", "down"), "data"
            ],
            f"weekend_bus_schedule_toward_{down_name}": self.raw_schedule_data.loc[
                (route_type, "weekend", "down"), "data"
            ],
        }

    def gen_bus_stops_info(self) -> list[dict]:
        """Generate bus stops information."""
        return [
            {
                "name": stop.name,
                "name_en": stop.name_en,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
            }
            for stop in stops.values()
        ]

    async def gen_bus_detailed_schedule_and_update_stops_data(self) -> None:
        """Generate detailed schedules and update stop data."""
        self._reset_stop_data()
        
        for route_type, day, direction in product(
            BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DAY, BUS_DIRECTION
        ):
            bus_schedule = self.raw_schedule_data.loc[
                (route_type, day, direction), "data"
            ]
            detailed_schedules = self._gen_detailed_bus_schedule(
                bus_schedule,
                route_type=route_type,
                day=day,
                direction=direction,
            )
            self.detailed_schedule_data.loc[(route_type, day, direction), "data"] = (
                detailed_schedules
            )

        gen_the_all_field(self.detailed_schedule_data, ["dep_info", "time"])

    def _reset_stop_data(self) -> None:
        """Reset stop data."""
        _init_stop_data()

    def _gen_detailed_bus_schedule(
        self,
        bus_schedule: list[dict],
        *,
        route_type: Literal["main", "nanda"] = "main",
        day: Literal["weekday", "weekend"] = "weekday",
        direction: Literal["up", "down"] = "up",
    ) -> list[dict]:
        """Generate detailed bus schedule with arrival times for each stop."""
        detailed_schedules: list[dict] = []
        for bus in bus_schedule:
            detailed_bus_schedule = self._process_single_bus_schedule(
                bus, route_type=route_type, day=day, direction=direction
            )
            detailed_schedules.append(detailed_bus_schedule)
        return detailed_schedules

    def _process_single_bus_schedule(
        self,
        bus: dict,
        *,
        route_type: Literal["main", "nanda"],
        day: Literal["weekday", "weekend"],
        direction: Literal["up", "down"],
    ) -> dict:
        """Process single bus schedule."""
        temp_bus: dict[str, Any] = {"dep_info": bus, "stops_time": []}
        route: Optional[models.Route] = self._select_bus_route(
            bus, route_type=route_type, day=day, direction=direction
        )

        if route:
            self._populate_stop_times_and_update_stop_data(
                temp_bus,
                bus,
                route,
                route_type=route_type,
                day=day,
                direction=direction,
            )
        return temp_bus

    def _select_bus_route(
        self,
        bus: dict,
        *,
        route_type: Literal["main", "nanda"],
        day: Literal["weekday", "weekend"],
        direction: Literal["up", "down"],
    ) -> Optional[models.Route]:
        """Select bus route based on bus info."""
        if route_type == "main":
            return self._select_main_bus_route(bus)
        elif route_type == "nanda":
            return self._select_nanda_bus_route(direction)
        return None

    def _select_main_bus_route(self, bus: dict) -> Optional[models.Route]:
        """Select main campus bus route."""
        dep_stop = bus.get("dep_stop", "")
        line = bus.get("line", "")
        dep_from_gen_2 = self._is_departure_from_gen_2(bus, line)
        if "綜二" in dep_stop:
            self._record_gen_2_departure_time(bus, line)
        return self._route_selector(dep_stop, line, dep_from_gen_2)

    def _select_nanda_bus_route(
        self, direction: Literal["up", "down"]
    ) -> Optional[models.Route]:
        """Select Nanda campus bus route."""
        return nanda_M1_S1 if direction == "up" else nanda_S1_M1

    def _is_departure_from_gen_2(self, bus: dict, line: str) -> bool:
        """Check if bus departs from Gen2."""
        bus_identifier = bus["time"] + line
        return bus_identifier in self._start_from_gen_2_bus_info or (
            "0" + bus["time"] + line in self._start_from_gen_2_bus_info
        )

    def _record_gen_2_departure_time(self, bus: dict, line: str) -> None:
        """Record Gen2 departure time."""
        self._start_from_gen_2_bus_info.append(self._add_on_time(bus["time"], 7) + line)

    def _route_selector(
        self, dep_stop: str, line: str, from_gen_2: bool = False
    ) -> Optional[models.Route]:
        """Select route based on departure stop and line."""
        dep_stop, line = dep_stop.strip(), line.strip()
        stops_lines_map: dict[tuple, models.Route] = {
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
        return stops_lines_map.get(key)

    def _populate_stop_times_and_update_stop_data(
        self,
        temp_bus: dict,
        bus: dict,
        route: models.Route,
        *,
        route_type: Literal["main", "nanda"],
        day: Literal["weekday", "weekend"],
        direction: Literal["up", "down"],
    ) -> None:
        """Populate stop times and update stop data."""
        accumulated_times = route.gen_accumulated_time()
        for i, (stop, acc_time) in enumerate(zip(route.stops, accumulated_times)):
            arrive_time = self._add_on_time(bus["time"], acc_time)
            temp_bus["stops_time"].append(
                {"stop": stop.name, "arrive_time": arrive_time}
            )

            # Update stop data
            stop_entry = {
                "arrive_time": arrive_time,
                "dep_time": bus["time"],
                "description": bus["description"],
                "bus_type": bus["bus_type"],
            }
            stop.stopped_bus_data[(route_type, day, direction)].append(stop_entry)

    def _add_on_time(self, start_time: str, time_delta: int) -> str:
        """Add minutes to time string."""
        st = datetime.strptime(start_time, "%H:%M") + timedelta(minutes=time_delta)
        return st.strftime("%H:%M")


# Global service instance
buses_service = BusesService()
