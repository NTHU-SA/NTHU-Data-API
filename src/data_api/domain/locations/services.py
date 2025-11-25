"""
Locations domain service.

Handles location/map data fetching and search.
"""

from typing import Optional

from thefuzz import fuzz

from data_api.data.manager import nthudata

JSON_PATH = "maps.json"
FUZZY_SEARCH_THRESHOLD = 60


class LocationsService:
    """Service for location data operations."""

    async def get_all_locations(self) -> tuple[Optional[str], list[dict]]:
        """Get all locations."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, map_data = result
        locations = [
            {
                "name": location_name,
                "latitude": coordinates["latitude"],
                "longitude": coordinates["longitude"],
            }
            for campus_locations in map_data.values()
            for location_name, coordinates in campus_locations.items()
        ]
        return commit_hash, locations

    async def fuzzy_search_locations(self, query: str) -> tuple[Optional[str], list[dict]]:
        """Fuzzy search locations by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, map_data = result
        tmp_results = []
        for campus_locations in map_data.values():
            for location_name, coordinates in campus_locations.items():
                similarity = fuzz.partial_ratio(query, location_name)
                if similarity >= FUZZY_SEARCH_THRESHOLD:
                    location = {
                        "name": location_name,
                        "latitude": coordinates["latitude"],
                        "longitude": coordinates["longitude"],
                    }
                    tmp_results.append((similarity, location))

        # Sort by exact match first, then by similarity
        tmp_results.sort(key=lambda x: (x[1]["name"] == query, x[0]), reverse=True)
        return commit_hash, [item[1] for item in tmp_results]


# Global service instance
locations_service = LocationsService()
