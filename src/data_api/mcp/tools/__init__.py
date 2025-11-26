"""
MCP Tools for NTHU Campus Assistant.

Each tool is in its own module for maintainability.
"""

from data_api.mcp.tools.announcements import _get_announcements, get_announcements
from data_api.mcp.tools.buses import (
    _get_bus_stops,
    _get_next_buses,
    get_bus_stops,
    get_next_buses,
)
from data_api.mcp.tools.campus import _search_campus, search_campus
from data_api.mcp.tools.courses import _search_courses, search_courses
from data_api.mcp.tools.dining import _find_dining, find_dining
from data_api.mcp.tools.energy import _get_energy_usage, get_energy_usage
from data_api.mcp.tools.library import _get_library_info, get_library_info
from data_api.mcp.tools.newsletters import _get_newsletters, get_newsletters

__all__ = [
    # Implementation functions (for testing)
    "_search_campus",
    "_get_next_buses",
    "_get_bus_stops",
    "_search_courses",
    "_get_announcements",
    "_find_dining",
    "_get_library_info",
    "_get_newsletters",
    "_get_energy_usage",
    # MCP tool wrappers
    "search_campus",
    "get_next_buses",
    "get_bus_stops",
    "search_courses",
    "get_announcements",
    "find_dining",
    "get_library_info",
    "get_newsletters",
    "get_energy_usage",
]
