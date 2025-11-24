"""
Buses domain service.
Handles data fetching, caching, and processing using the Graph module.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from itertools import product
from typing import Any, Literal, Optional, cast

from data_api.core import constants
from data_api.data.manager import nthudata
from data_api.domain.buses import enums, models, graph

# Constants
DATA_TTL_HOURS = constants.DATA_TTL_HOURS

# Type lists
BUS_ROUTE_TYPE = [t.value for t in enums.BusRouteType]
BUS_ROUTE_TYPE_WITHOUT_ALL = [t for t in BUS_ROUTE_TYPE if t != "all"]
BUS_DAY = [d.value for d in enums.BusDay]
BUS_DIRECTION = [d.value for d in enums.BusDirection]
BUS_DIRECTION_WITHOUT_ALL = [d for d in BUS_DIRECTION if d != "all"]

ScheduleKey = tuple[str, str, str]
ScheduleStore = dict[ScheduleKey, list[dict[str, Any]]]
RouteInfoKey = tuple[str, str]


# --- Helper Functions ---
def after_specific_time(
    target_list: list[dict], time_str: str, time_keys: list[str]
) -> list[dict]:
    """Filter list to keep only items after specified time."""
    if not time_str or not target_list:
        return target_list or []

    try:
        ref_time = datetime.strptime(time_str, "%H:%M")
        filtered = []
        for item in target_list:
            val = item
            for k in time_keys:
                if isinstance(val, dict):
                    val = val.get(k)
                else:
                    val = None
                    break

            if not isinstance(val, str):
                continue

            try:
                item_time = datetime.strptime(val, "%H:%M")
                if item_time >= ref_time:
                    filtered.append(item)
            except ValueError:
                continue
        return filtered
    except ValueError:
        return []


def add_time(time_str: str, minutes: int) -> str:
    """Add minutes to HH:MM string safely."""
    try:
        dt = datetime.strptime(time_str, "%H:%M") + timedelta(minutes=minutes)
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return time_str


def sort_by_time(target: list[dict], time_keys: list[str]) -> None:
    def get_sort_key(x):
        val = x
        for k in time_keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                val = None
                break
        if not isinstance(val, str):
            return datetime.max
        try:
            return datetime.strptime(val, "%H:%M")
        except (ValueError, TypeError):
            return datetime.max  # Push invalid to end

    target.sort(key=get_sort_key)


class BusesService:
    """Bus schedule management service."""

    def __init__(self) -> None:
        self.raw_schedule_data = self._new_schedule_store()
        self.detailed_schedule_data = self._new_schedule_store()
        self._route_info: dict[RouteInfoKey, dict[str, Any]] = {}

        # Stop data aggregation (Stop ID -> {(RouteType, Day, Direction) -> List[Items]})
        self.stops_schedule_registry: dict[
            str, dict[ScheduleKey, list[dict[str, Any]]]
        ] = {}

        self.last_commit_hash = None
        self._res_json: dict[str, Any] = {}
        self._gen2_departures: set[str] = set()

    def _new_schedule_store(self) -> ScheduleStore:
        return {
            (rtype, day, direction): []
            for rtype, day, direction in product(BUS_ROUTE_TYPE, BUS_DAY, BUS_DIRECTION)
        }

    async def update_data(self) -> None:
        """Update bus schedule data from remote source."""
        result = await nthudata.get("buses.json")
        if result is None:
            if self.last_commit_hash is None:
                print("Warning: Could not fetch buses.json and no cache available.")
            return

        res_commit_hash, payload = result
        if not isinstance(payload, dict):
            return

        self._res_json = payload

        if self._res_json and res_commit_hash != self.last_commit_hash:
            self._process_all_data()
            self.last_commit_hash = res_commit_hash

    def _process_all_data(self) -> None:
        """Main processing pipeline."""
        self._reset_registries()
        self._populate_info_data()
        self._populate_raw_schedule()
        self._generate_detailed_schedule_and_stops()
        self._sort_schedule_store(self.raw_schedule_data, ["time"])
        self._sort_schedule_store(self.detailed_schedule_data, ["dep_info", "time"])
        self._sort_stop_registry_lists()
        self._derive_combined_views()

    def _reset_registries(self) -> None:
        self._gen2_departures.clear()
        self.raw_schedule_data = self._new_schedule_store()
        self.detailed_schedule_data = self._new_schedule_store()
        self._route_info = {}
        self.stops_schedule_registry = {s_id: {} for s_id in graph.STOPS_DATA.keys()}

    # --- 1. Info Data ---
    def _populate_info_data(self) -> None:
        mapping = {
            ("main", "up"): "towardTSMCBuildingInfo",
            ("main", "down"): "towardMainGateInfo",
            ("nanda", "up"): "towardNandaInfo",
            ("nanda", "down"): "towardMainCampusInfo",
        }
        for (rtype, rdir), json_key in mapping.items():
            self._route_info[(rtype, rdir)] = self._res_json.get(json_key, {})

    # --- 2. Raw Schedule ---
    def _populate_raw_schedule(self) -> None:
        for rtype, day, rdir in product(
            BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DAY, BUS_DIRECTION_WITHOUT_ALL
        ):
            toward_name = ""
            if rtype == "main":
                toward_name = "TSMCBuilding" if rdir == "up" else "MainGate"
            elif rtype == "nanda":
                toward_name = "Nanda" if rdir == "up" else "MainCampus"

            key = f"{day}BusScheduleToward{toward_name}"
            raw_list = self._res_json.get(key, [])

            enhanced_list = []
            for item in raw_list:
                bus = item.copy()
                bus["bus_type"] = self._classify_bus_type(
                    rtype, day, bus.get("description", "")
                )

                if rtype == "nanda":
                    bus["dep_stop"] = "校門" if rdir == "up" else "南大"

                if rtype == "main" and "綜二" in bus.get("dep_stop", ""):
                    line = bus.get("line", "")
                    time = bus.get("time", "")
                    predicted_gate_time = add_time(time, 7)
                    self._gen2_departures.add(f"{predicted_gate_time}{line}")
                    self._gen2_departures.add(f"0{predicted_gate_time}{line}")

                enhanced_list.append(bus)

            self.raw_schedule_data[(rtype, day, rdir)] = enhanced_list

    def _classify_bus_type(self, rtype: str, day: str, desc: str) -> str:
        if rtype == "nanda" and "83" in desc:
            return enums.BusType.route_83.value
        if (rtype == "main" and "大" in desc) or (
            rtype == "nanda" and day == "weekday"
        ):
            return enums.BusType.large_sized_bus.value
        return enums.BusType.middle_sized_bus.value

    # --- 3. Detailed Schedule & Route Calculation ---
    def _generate_detailed_schedule_and_stops(self) -> None:
        for rtype, day, rdir in product(
            BUS_ROUTE_TYPE_WITHOUT_ALL, BUS_DAY, BUS_DIRECTION_WITHOUT_ALL
        ):
            raw_list = self.raw_schedule_data.get((rtype, day, rdir), [])
            if not isinstance(raw_list, list):
                continue

            detailed_list = []

            for bus in raw_list:
                route = self._get_route_from_graph(bus, rtype, rdir)
                stops_time_info = []

                if route:
                    start_time = bus.get("time", "00:00")
                    for stop, offset in zip(route.stops, route.time_offsets):
                        arr_time = add_time(start_time, offset)
                        stops_time_info.append(
                            {"stop": stop.name, "arrive_time": arr_time}
                        )
                        self._add_to_stop_registry(
                            stop.id,
                            rtype,
                            day,
                            rdir,
                            {
                                "arrive_time": arr_time,
                                "dep_time": start_time,
                                "dep_stop": bus.get("dep_stop", ""),
                                "description": bus.get("description", ""),
                                "bus_type": bus.get("bus_type", ""),
                            },
                        )

                detailed_list.append(
                    {
                        "dep_info": bus,
                        "stops_time": stops_time_info,
                        "bus_type": bus.get("bus_type", ""),
                    }
                )

            self.detailed_schedule_data[(rtype, day, rdir)] = detailed_list

    def _get_route_from_graph(
        self, bus: dict, rtype: str, rdir: str
    ) -> Optional[models.Route]:
        if rtype == "main":
            line = bus.get("line", "")
            dep_stop = bus.get("dep_stop", "")
            time_val = bus.get("time", "")

            identifier = f"{time_val}{line}"
            is_from_gen2 = (
                identifier in self._gen2_departures
                or f"0{identifier}" in self._gen2_departures
            )

            return graph.resolver.resolve_main_campus_route(
                line, dep_stop, is_from_gen2
            )

        if rtype == "nanda":
            direction = cast(Literal["up", "down"], rdir)
            return graph.resolver.resolve_nanda_route(
                direction, bus.get("description", "")
            )

        return None

    def _add_to_stop_registry(
        self, stop_id: str, rtype: str, day: str, rdir: str, data: dict
    ) -> None:
        stop_data = self.stops_schedule_registry.setdefault(stop_id, {})
        stop_data.setdefault((rtype, day, rdir), []).append(data)

    def _sort_schedule_store(self, store: ScheduleStore, time_path: list[str]) -> None:
        for entries in store.values():
            if isinstance(entries, list) and entries:
                sort_by_time(entries, time_path)

    def _sort_stop_registry_lists(self) -> None:
        for stop_data in self.stops_schedule_registry.values():
            for entries in stop_data.values():
                if entries:
                    sort_by_time(entries, ["arrive_time"])

    # --- 4. Post-Processing ("All" fields) ---
    def _derive_combined_views(self) -> None:
        self._combine_route_types_for_store(self.raw_schedule_data, ["time"])
        self._combine_route_types_for_store(
            self.detailed_schedule_data, ["dep_info", "time"]
        )
        self._combine_route_types_for_stops()

        self._combine_directions_for_store(self.raw_schedule_data, ["time"])
        self._combine_directions_for_store(
            self.detailed_schedule_data, ["dep_info", "time"]
        )
        self._combine_directions_for_stops()

    def _combine_route_types_for_store(
        self, store: ScheduleStore, time_path: list[str]
    ) -> None:
        for day, rdir in product(BUS_DAY, BUS_DIRECTION_WITHOUT_ALL):
            combined = [
                *store.get(("main", day, rdir), []),
                *store.get(("nanda", day, rdir), []),
            ]
            if combined:
                sort_by_time(combined, time_path)
            store[("all", day, rdir)] = combined

    def _combine_directions_for_store(
        self, store: ScheduleStore, time_path: list[str]
    ) -> None:
        for rtype, day in product(BUS_ROUTE_TYPE, BUS_DAY):
            combined = [
                *store.get((rtype, day, "up"), []),
                *store.get((rtype, day, "down"), []),
            ]
            if combined:
                sort_by_time(combined, time_path)
            store[(rtype, day, "all")] = combined

    def _combine_route_types_for_stops(self) -> None:
        for stop_data in self.stops_schedule_registry.values():
            for day, rdir in product(BUS_DAY, BUS_DIRECTION_WITHOUT_ALL):
                combined = [
                    *stop_data.get(("main", day, rdir), []),
                    *stop_data.get(("nanda", day, rdir), []),
                ]
                if combined:
                    sort_by_time(combined, ["arrive_time"])
                stop_data[("all", day, rdir)] = combined

    def _combine_directions_for_stops(self) -> None:
        for stop_data in self.stops_schedule_registry.values():
            for rtype, day in product(BUS_ROUTE_TYPE, BUS_DAY):
                combined = [
                    *stop_data.get((rtype, day, "up"), []),
                    *stop_data.get((rtype, day, "down"), []),
                ]
                if combined:
                    sort_by_time(combined, ["arrive_time"])
                stop_data[(rtype, day, "all")] = combined

    def _get_route_data_bundle(self, rtype: str) -> dict:
        mapping_name = "TSMC_building" if rtype == "main" else "nanda"
        down_name = "main_gate" if rtype == "main" else "main_campus"

        def gd(day: str, rdir: str) -> list[dict]:
            return self.raw_schedule_data.get((rtype, day, rdir), [])

        def gi(rdir: str) -> dict:
            return self._route_info.get((rtype, rdir)) or {}

        directions = {
            "up": mapping_name,
            "down": down_name,
        }

        bundle = {}
        for rdir, name in directions.items():
            bundle[f"toward_{name}_info"] = gi(rdir)
            bundle[f"weekday_bus_schedule_toward_{name}"] = gd("weekday", rdir)
            bundle[f"weekend_bus_schedule_toward_{name}"] = gd("weekend", rdir)

        return bundle

    def get_route_info(
        self, route_type: Optional[str], direction: Optional[str]
    ) -> list[dict]:
        # 用篩選條件取得路線資訊
        results = []
        for (rtype, rdir), info in self._route_info.items():
            if (route_type is None or route_type == rtype) and (
                direction is None or direction == rdir
            ):
                results.append(info)
        return results

    def get_schedule(
        self, *, route_type: str, day: str, direction: str, detailed: bool = False
    ) -> list[dict]:
        store = self.detailed_schedule_data if detailed else self.raw_schedule_data
        return store.get((route_type, day, direction), [])

    def gen_bus_stops_info(self) -> list[dict]:
        return [
            {
                "name": s.name,
                "name_en": s.name_en,
                "latitude": s.latitude,
                "longitude": s.longitude,
            }
            for s in graph.STOPS_DATA.values()
        ]

    def get_stop_schedule(
        self, stop_name: str, rtype: str, day: str, rdir: str
    ) -> list[dict]:
        stop_id = next(
            (k for k, v in graph.STOPS_DATA.items() if v.name == stop_name), None
        )
        if not stop_id:
            return []

        registry_data = self.stops_schedule_registry.get(stop_id, {})
        return registry_data.get((rtype, day, rdir), [])


# Global Instance
buses_service = BusesService()
