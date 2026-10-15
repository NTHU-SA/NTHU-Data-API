"""Location search MCP tool."""

from data_api.mcp.server import mcp
from data_api.mcp.tools.result_types import LocationsResult
from data_api.runtime import get_runtime


async def _search_locations(query: str, fuzzy: bool = True) -> LocationsResult:
    """Search location names before applying the result cap."""
    service = get_runtime().locations
    if fuzzy:
        _, locations = await service.fuzzy_search_locations(query=query)
    else:
        _, locations = await service.get_locations(name=query)
        # The REST-oriented service treats an empty name as an unfiltered listing.
        locations = [location for location in locations if location["name"] == query]
    return {"locations": locations[:5]}


@mcp.tool(
    name="search_locations",
    title="搜尋校園地點",
    description="Search NTHU campus locations and building coordinates. "
    "Returns up to 5 locations. Fuzzy matching is enabled by default; "
    "set fuzzy=false for case-sensitive full-string equality. "
    "Use search_directory instead for department or staff contact information.",
)
async def search_locations(query: str, fuzzy: bool = True) -> dict:
    """Search campus locations using fuzzy or exact matching."""
    return await _search_locations(query, fuzzy=fuzzy)
