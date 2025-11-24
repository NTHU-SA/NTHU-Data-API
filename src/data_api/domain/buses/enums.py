"""
Bus domain enums.

This module contains all enumerations used in the bus domain.
Moved from schemas to keep domain independent of Pydantic.
"""

from enum import Enum


class BusStopsName(str, Enum):
    """Bus stop names."""

    M1 = "北校門口"
    M2 = "綜二館"
    M3 = "楓林小徑"
    M4 = "人社院&生科館"
    M5 = "台積館"
    M6 = "奕園停車場"
    M7 = "教育學院大樓&南門停車場"
    S1 = "南大校區校門口右側(食品路校牆邊)"


class BusRouteType(str, Enum):
    """Bus route type."""

    all = "all"
    main = "main"
    nanda = "nanda"


class BusType(str, Enum):
    """Bus vehicle type."""

    route_83 = "route_83"
    large_sized_bus = "large-sized_bus"
    middle_sized_bus = "middle-sized_bus"


class BusDirection(str, Enum):
    """Bus direction."""

    all = "all"
    up = "up"
    down = "down"


class BusDay(str, Enum):
    """Day type for bus schedule."""

    weekday = "weekday"
    weekend = "weekend"


class BusDayWithCurrent(str, Enum):
    """Day type including current day option."""

    weekday = "weekday"
    weekend = "weekend"
    current = "current"
