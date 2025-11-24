"""
Bus domain models.

Pure Python domain models without FastAPI or Pydantic dependencies.
These represent the core business entities in the bus domain.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(unsafe_hash=True)
class Stop:
    """
    Bus stop data model.

    Attributes:
        name: Chinese name of the stop.
        name_en: English name of the stop.
        latitude: Latitude coordinate as string.
        longitude: Longitude coordinate as string.
        stopped_bus_data: Dictionary storing bus schedule data by route/day/direction.
                          Initialized after creation, not part of comparison/hash.
    """

    name: str
    name_en: str
    latitude: str
    longitude: str
    stopped_bus_data: dict[tuple[str, str, str], list[dict[str, Any]]] = field(
        init=False, compare=False, hash=False, default_factory=dict
    )


@dataclass
class Route:
    """
    Bus route data model.

    Attributes:
        stops: List of Stop objects in route order.
        delta_time_table: Dictionary mapping stop pairs to travel time in minutes.
    """

    stops: list[Stop]
    delta_time_table: dict[Stop, dict[Stop, int]] = field(default_factory=dict)

    def gen_accumulated_time(self) -> list[int]:
        """
        Calculate cumulative travel time for each stop on the route.

        Returns:
            List of cumulative times in minutes, starting from 0.
        """
        acc_times = [0]
        for i in range(len(self.stops) - 1):
            acc_times.append(
                acc_times[i] + self.delta_time_table[self.stops[i]][self.stops[i + 1]]
            )
        return acc_times


@dataclass
class BusInfo:
    """Bus route information."""

    direction: str
    duration: str
    route: str
    route_en: str


@dataclass
class BusSchedule:
    """Basic bus schedule entry."""

    time: str
    description: str
    bus_type: str


@dataclass
class BusMainSchedule(BusSchedule):
    """Main campus bus schedule entry."""

    pass


@dataclass
class BusNandaSchedule(BusSchedule):
    """Nanda campus bus schedule entry with departure stop."""

    dep_stop: str = ""


@dataclass
class BusDetailedSchedule:
    """Detailed bus schedule with arrival times at each stop."""

    dep_info: dict[str, str]  # departure information: {"time": "HH:MM", "description": "..."}
    arr_info: list[dict[str, str]]  # arrival info: [{"stop": "...", "arrive_time": "HH:MM"}, ...]
    bus_type: str


@dataclass
class BusStopInfo:
    """Bus stop information."""

    name: str
    name_en: str
    latitude: str
    longitude: str


@dataclass
class BusStopsQueryResult:
    """Result of querying bus stops."""

    arrive_time: str
    dep_time: str
    description: str
    bus_type: str
