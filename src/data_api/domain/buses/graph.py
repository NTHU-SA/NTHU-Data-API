"""
Buses graph definition.
Contains Route topology, Stop definitions, and Route selection logic.
"""

from typing import Literal, Optional

from . import models

# --- 1. Stop Definitions ---
STOPS_DATA = {
    "M1": models.Stop("M1", "北校門口", "North Main Gate", "24.79589", "120.99633"),
    "M2": models.Stop("M2", "綜二館", "General Building II", "24.79417", "120.99376"),
    "M3": models.Stop("M3", "楓林小徑", "Maple Path", "24.79138", "120.99138"),
    "M4": models.Stop("M4", "人社院&生科館", "CHSS/CLS Building", "24.78973", "120.99001"),
    "M5": models.Stop("M5", "台積館", "TSMC Building", "24.78695", "120.9884"),
    "M6": models.Stop("M6", "奕園停車場", "Yi Pavilion Parking Lot", "24.78828", "120.99246"),
    "M7": models.Stop(
        "M7",
        "教育學院大樓&南門停車場",
        "COE Building/South Gate Parking Lot",
        "24.78593",
        "120.99013",
    ),
    "S1": models.Stop(
        "S1",
        "南大校區校門口右側(食品路校牆邊)",
        "The right side of NandaCampus front gate",
        "24.79438",
        "120.96538",
    ),
}

# Helper to access stops easily
S = STOPS_DATA

# --- 2. Route Factory Helpers ---


def create_route(route_id: str, stop_ids: list[str], deltas: list[int]) -> models.Route:
    """
    Creates a Route object with pre-calculated time offsets.
    stop_ids: ["M1", "M2", ...]
    deltas: [1, 2, ...] -> Time to travel FROM previous stop TO current stop.
            First element is usually 0 (time to reach first stop).
    """
    stops = [S[sid] for sid in stop_ids]

    # Calculate cumulative time offsets
    # If deltas is [0, 1, 1, 2], offsets are [0, 1, 2, 4]
    offsets = [0] * len(stops)
    current_time = 0
    for i, time_needed in enumerate(deltas):
        current_time += time_needed
        if i < len(offsets):
            offsets[i] = current_time

    return models.Route(id=route_id, stops=stops, time_offsets=offsets)


# --- 3. Route Definitions (The Graph) ---

# Red Lines
# M1 -> M2 (1m) -> M3 (1m) -> M4 (2m) -> M5 (2m)
red_M1_M5 = create_route("red_M1_M5", ["M1", "M2", "M3", "M4", "M5"], [0, 1, 1, 2, 2])
# M2 -> M3 (1m) -> M4 (2m) -> M5 (2m) (Start from Gen 2)
red_M2_M5 = create_route("red_M2_M5", ["M2", "M3", "M4", "M5"], [0, 1, 2, 2])
# M5 -> M7 (1m) -> M6 (2m) -> M2 (1m) -> M1 (1m)
red_M5_M1 = create_route("red_M5_M1", ["M5", "M7", "M6", "M2", "M1"], [0, 1, 2, 1, 1])
# M5 -> M7 (1m) -> M6 (2m) -> M2 (1m) (End at Gen 2)
red_M5_M2 = create_route("red_M5_M2", ["M5", "M7", "M6", "M2"], [0, 1, 2, 1])

# Green Lines
# M1 -> M2 (1m) -> M3 (1m) -> M6 (1m) -> M7 (2m) -> M5 (1m)
green_M1_M5 = create_route("green_M1_M5", ["M1", "M2", "M3", "M6", "M7", "M5"], [0, 1, 1, 1, 2, 1])
green_M2_M5 = create_route("green_M2_M5", ["M2", "M3", "M6", "M7", "M5"], [0, 1, 1, 2, 1])
# M5 -> M4 (2m) -> M2 (3m) -> M1 (1m)
green_M5_M1 = create_route("green_M5_M1", ["M5", "M4", "M2", "M1"], [0, 2, 3, 1])
green_M5_M2 = create_route("green_M5_M2", ["M5", "M4", "M2"], [0, 2, 3])

# Nanda Lines
# Route 1: M1 -> M2 (1m) -> M4 (2m) -> M5 (2m) -> S1 (15m) (Estimated)
nanda_M1_S1_r1 = create_route("nanda_M1_S1_r1", ["M1", "M2", "M4", "M5", "S1"], [0, 1, 2, 2, 15])
# Route 2: M1 -> M2 (1m) -> M6 (4m) -> M7 (2m) -> S1 (15m)
nanda_M1_S1_r2 = create_route("nanda_M1_S1_r2", ["M1", "M2", "M6", "M7", "S1"], [0, 1, 4, 2, 15])

# Return: S1 -> M5 (15m) -> M4 (2m) -> M2 (2m) -> M1 (1m)
nanda_S1_M1_r1 = create_route("nanda_S1_M1_r1", ["S1", "M5", "M4", "M2", "M1"], [0, 15, 2, 2, 1])
# Return Route 2: S1 -> M7 (15m) -> M6 (2m) -> M2 (4m) -> M1 (1m)
nanda_S1_M1_r2 = create_route("nanda_S1_M1_r2", ["S1", "M7", "M6", "M2", "M1"], [0, 15, 2, 4, 1])


# --- 4. Route Resolver Logic ---


class RouteResolver:
    """Encapsulates the logic to determine which Route object matches a bus schedule."""

    @staticmethod
    def resolve_main_campus_route(
        line: str, dep_stop: str, is_from_gen2: bool = False
    ) -> Optional[models.Route]:
        """
        Resolves main campus routes (Red/Green).
        line: 'red' or 'green'
        dep_stop: '台積館' or '校門' or '綜二'
        is_from_gen2: Special flag if inferred from schedule gap.
        """
        # Normalize inputs
        line = line.lower()

        # 1. Determine Direction & Variant
        if "台積" in dep_stop:
            # Downhill (TSMC -> Gate)
            if line == "red":
                return red_M5_M2 if is_from_gen2 else red_M5_M1
            elif line == "green":
                return green_M5_M2 if is_from_gen2 else green_M5_M1

        elif "校門" in dep_stop or "北校" in dep_stop:
            # Uphill (Gate -> TSMC)
            if line == "red":
                return red_M1_M5
            elif line == "green":
                return green_M1_M5

        elif "綜二" in dep_stop:
            # Starting from middle
            if line == "red":
                return red_M2_M5
            elif line == "green":
                return green_M2_M5

        return None

    @staticmethod
    def resolve_nanda_route(direction: Literal["up", "down"], description: str) -> models.Route:
        """
        Resolves Nanda routes based on description logic.
        direction: 'up' (Main -> Nanda) or 'down' (Nanda -> Main)
        """
        description = description or ""
        is_route_2 = "路線二" in description or "教育學院" in description

        if direction == "down":
            # Going back to Main Campus
            return nanda_S1_M1_r2 if is_route_2 else nanda_S1_M1_r1
        else:
            # Going to Nanda
            return nanda_M1_S1_r2 if is_route_2 else nanda_M1_S1_r1

    @staticmethod
    def get_nanda_line(description: str) -> str:
        """
        Determines the Nanda route line from the description.

        Route detection logic:
        - Route 2: If description contains "路線二" or "教育學院"
        - Route 1: All other cases (default)

        Args:
            description: Bus schedule description text

        Returns:
            'route_1' or 'route_2'

        Examples:
            >>> get_nanda_line("路線二經過教育學院")
            'route_2'
            >>> get_nanda_line("一般路線")
            'route_1'
        """
        description = description or ""
        is_route_2 = "路線二" in description or "教育學院" in description
        return "route_2" if is_route_2 else "route_1"


# Instantiate global resolver
resolver = RouteResolver()
