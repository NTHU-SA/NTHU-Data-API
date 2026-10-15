"""
NTHU Data API MCP Server.

Curated MCP tools designed for LLM agents, following agent-first design principles:
1. Minimal tool count - combine related functionality
2. LLM-friendly names and descriptions in natural language
3. Reasonable defaults to hide complexity
4. Focus on agent stories rather than API structure

These tools are designed to answer common questions about NTHU campus life.
"""

from typing import TYPE_CHECKING

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from data_api import __version__
from data_api.core.exceptions import DataNotAvailableException

if TYPE_CHECKING:
    from data_api.runtime import Runtime


class DatasetErrors(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        try:
            return await call_next(context)
        except DataNotAvailableException as exc:
            raise ToolError("Dataset temporarily unavailable. Please try again later.") from exc
        except ToolError as exc:
            # FastMCP wraps execution failures before middleware sees them.
            if isinstance(exc.__cause__, DataNotAvailableException):
                raise ToolError("Dataset temporarily unavailable. Please try again later.") from exc
            raise


# Create curated MCP server
mcp = FastMCP(
    name="NTHU Campus Assistant",
    version=__version__,
    mask_error_details=True,
    instructions="""You are an assistant for National Tsing Hua University (NTHU) in Taiwan.
You can help with:
- Finding campus locations and directions
- Looking up departments and staff contact information
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
mcp.add_middleware(DatasetErrors())


def create_mcp(runtime: "Runtime") -> FastMCP:
    """Reuse tool definitions, not the HTTP session manager or runtime state."""
    from data_api.runtime import bind_runtime

    class RuntimeBinding(Middleware):
        async def on_call_tool(self, context: MiddlewareContext, call_next):
            with bind_runtime(runtime):
                return await call_next(context)

    return FastMCP(
        name=mcp.name,
        version=mcp.version,
        instructions=mcp.instructions,
        providers=[mcp.local_provider],
        middleware=[RuntimeBinding(), DatasetErrors()],
        mask_error_details=True,
    )


# Import tools after mcp is created to avoid circular imports
# Tools register themselves with the mcp instance when imported
from data_api.mcp.tools import (  # noqa: E402, F401
    _find_dining,
    _get_announcements,
    _get_bus_schedule,
    _get_energy_usage,
    _get_library_info,
    _get_newsletters,
    _search_courses,
    _search_directory,
    _search_locations,
    find_dining,
    get_announcements,
    get_bus_schedule,
    get_energy_usage,
    get_library_info,
    get_newsletters,
    search_courses,
    search_directory,
    search_locations,
)

__all__ = [
    "mcp",
    # Implementation functions (for testing)
    "_search_directory",
    "_search_locations",
    "_get_bus_schedule",
    "_search_courses",
    "_get_announcements",
    "_find_dining",
    "_get_library_info",
    "_get_newsletters",
    "_get_energy_usage",
    # MCP tool wrappers
    "search_directory",
    "search_locations",
    "get_bus_schedule",
    "search_courses",
    "get_announcements",
    "find_dining",
    "get_library_info",
    "get_newsletters",
    "get_energy_usage",
]
