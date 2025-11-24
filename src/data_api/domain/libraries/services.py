"""
Libraries domain service.

Handles library data fetching and search.
"""

from typing import Optional

from data_api.data.manager import nthudata
from thefuzz import fuzz

JSON_PATH = "libraries.json"
FUZZY_SEARCH_THRESHOLD = 70


class LibrariesService:
    """Service for library data operations."""

    async def get_all_libraries(self) -> tuple[Optional[str], list[dict]]:
        """Get all libraries."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []
        return result

    async def get_library_by_name(
        self, name: str
    ) -> tuple[Optional[str], Optional[dict]]:
        """Get library by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, None

        commit_hash, libraries_data = result
        for library in libraries_data:
            if library["name"] == name:
                return commit_hash, library
        return commit_hash, None

    async def fuzzy_search_libraries(
        self, query: str
    ) -> tuple[Optional[str], list[dict]]:
        """Fuzzy search libraries by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, libraries_data = result
        results_with_score = []
        for library in libraries_data:
            similarity = fuzz.partial_ratio(query, library["name"])
            if similarity >= FUZZY_SEARCH_THRESHOLD:
                results_with_score.append((similarity, library))

        results_with_score.sort(key=lambda x: x[0], reverse=True)
        return commit_hash, [lib for _, lib in results_with_score]


# Global service instance
libraries_service = LibrariesService()
