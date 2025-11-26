"""Campus search MCP tool."""

from data_api.domain.departments import services as departments_services
from data_api.domain.locations import services as locations_services
from data_api.mcp.server import mcp


async def _search_campus(query: str) -> dict:
    """
    Search for campus locations, departments, or people.

    Args:
        query: Search term - can be a location name, department name, or person's name.

    Returns:
        Dictionary with locations, departments, and people matching the query.
    """
    # Search locations
    _, locations = await locations_services.locations_service.fuzzy_search_locations(query=query)

    # Search departments and people
    _, dept_results = (
        await departments_services.departments_service.fuzzy_search_departments_and_people(
            query=query
        )
    )

    return {
        "locations": locations[:5] if locations else [],
        "departments": dept_results.get("departments", [])[:5],
        "people": dept_results.get("people", [])[:10],
    }


@mcp.tool(
    description="Search for campus locations, departments, or people at NTHU. "
    "Use this to find where buildings are, contact info for departments, or look up staff members."
)
async def search_campus(query: str) -> dict:
    """Search for campus locations, departments, or people."""
    return await _search_campus(query)
