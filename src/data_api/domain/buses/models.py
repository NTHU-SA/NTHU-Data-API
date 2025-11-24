"""
Buses domain models.
Pure Python domain models representing business entities.
"""

from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class Stop:
    """Bus stop data model."""

    id: str  # Added ID for easier lookup (e.g., "M1")
    name: str
    name_en: str
    latitude: str
    longitude: str


@dataclass
class Route:
    """Bus route data model."""

    id: str  # e.g., "Red_M1_M5"
    stops: list[Stop]
    # time_offsets[i] = minutes from start stop to stops[i]
    time_offsets: list[int]


@dataclass
class BusSchedule:
    """Basic bus schedule entry from raw JSON."""

    time: str
    description: str
    bus_type: str
    line: str = ""  # Main campus: red/green, Nanda: route_1/route_2
    dep_stop: str = ""


@dataclass
class BusDetailedSchedule:
    """Processed schedule with arrival times."""

    dep_info: dict[str, str]  # {"time": "...", "description": "..."}
    arr_info: list[dict[str, str]]  # [{"stop": "...", "arrive_time": "..."}]
    bus_type: str
