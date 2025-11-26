"""
NTHU Data API MCP Server.

Curated MCP tools designed for LLM agents, following agent-first design principles:
1. Minimal tool count - combine related functionality
2. LLM-friendly names and descriptions in natural language
3. Reasonable defaults to hide complexity
4. Focus on agent stories rather than API structure

These tools are designed to answer common questions about NTHU campus life.
"""

from fastmcp import FastMCP

# Create curated MCP server
mcp = FastMCP(
    name="NTHU Campus Assistant",
    instructions="""You are an assistant for National Tsing Hua University (NTHU) in Taiwan.
You can help with:
- Finding campus locations and directions
- Checking bus schedules and next arrivals
- Searching for courses
- Getting campus announcements
- Finding restaurants and dining options
- Checking library information
- Getting newsletter updates
- Checking real-time electricity usage

Always respond in the user's language (Traditional Chinese or English).
""",
)

# Import tools after mcp is created to avoid circular imports
# Tools register themselves with the mcp instance when imported
from data_api.mcp.tools import (  # noqa: E402, F401
    _find_dining,
    _get_announcements,
    _get_bus_stops,
    _get_energy_usage,
    _get_library_info,
    _get_newsletters,
    _get_next_buses,
    _search_campus,
    _search_courses,
    find_dining,
    get_announcements,
    get_bus_stops,
    get_energy_usage,
    get_library_info,
    get_newsletters,
    get_next_buses,
    search_campus,
    search_courses,
)

__all__ = [
    "mcp",
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
