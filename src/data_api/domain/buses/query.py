"""Resolve bus query time independently of its REST or MCP transport."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BusTimeState:
    day: str
    after_time: str
    current_time: str


def resolve_bus_time(day: str, time: str | None, current: datetime) -> BusTimeState:
    current_time = current.strftime("%H:%M")
    if day == "current":
        return BusTimeState(
            "weekday" if current.weekday() < 5 else "weekend", current_time, current_time
        )
    return BusTimeState(day, time or "", current_time)
