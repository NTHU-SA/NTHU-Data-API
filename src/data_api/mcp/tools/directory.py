"""Directory search MCP tool."""

from data_api.mcp.server import mcp
from data_api.mcp.tools.result_types import DirectoryResult
from data_api.runtime import get_runtime


async def _search_directory(query: str, fuzzy: bool = True) -> DirectoryResult:
    """Search department names, person names, or titles before applying result caps."""
    _, results = await get_runtime().departments.search_departments_and_people(
        query=query, fuzzy=fuzzy
    )
    return {
        "departments": results["departments"][:5],
        "people": results["people"][:10],
    }


@mcp.tool(
    name="search_directory",
    title="搜尋清華通訊錄",
    description="Search NTHU department names, staff names, or titles for contact information. "
    "Returns up to 5 departments and 10 people. Fuzzy matching is enabled by default; "
    "set fuzzy=false for case-sensitive full-string equality. "
    "Use search_locations instead to find campus buildings or coordinates.",
)
async def search_directory(query: str, fuzzy: bool = True) -> dict:
    """Search the directory using fuzzy or exact matching."""
    return await _search_directory(query, fuzzy=fuzzy)
