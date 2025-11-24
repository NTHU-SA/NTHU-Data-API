"""
Dining domain service.

Handles business logic for dining data fetching and filtering.
"""

from datetime import datetime
from typing import Optional

from thefuzz import fuzz

from data_api.data.manager import nthudata
from data_api.domain.dining import enums

JSON_PATH = "dining.json"
FUZZY_SEARCH_THRESHOLD = 60


def is_restaurant_open(restaurant: dict, day: str) -> bool:
    """
    Check if restaurant is open on specified day.

    Args:
        restaurant: Restaurant data dict
        day: Day of week in English lowercase

    Returns:
        True if restaurant may be open, False if definitely closed
    """
    note = restaurant.get("note", "").lower()
    for keyword in enums.DiningScheduleKeyword.BREAK_KEYWORDS:
        for day_zh in enums.DiningScheduleKeyword.DAY_EN_TO_ZH.get(day, []):
            if keyword in note and day_zh in note:
                return False
    return True


class DiningService:
    """Service for dining data operations."""

    async def get_dining_data(
        self, building_name: Optional[str] = None
    ) -> tuple[Optional[str], list[dict]]:
        """Get dining data with optional building filter."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, dining_data = result

        if building_name:
            dining_data = [
                building
                for building in dining_data
                if building["building"] == building_name
            ]

        return commit_hash, dining_data

    async def get_open_restaurants(
        self, schedule: str
    ) -> tuple[Optional[str], list[dict]]:
        """Get currently open restaurants based on schedule."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, dining_data = result

        open_restaurants = []
        for building in dining_data:
            for restaurant in building["restaurants"]:
                if schedule == "today":
                    current_day = datetime.now().strftime("%A").lower()
                    if current_day in ["saturday", "sunday"]:
                        day = current_day
                    else:
                        day = "weekday"
                else:
                    day = schedule

                if is_restaurant_open(restaurant, day):
                    open_restaurants.append(restaurant)

        return commit_hash, open_restaurants

    async def fuzzy_search_restaurants(
        self, query: str
    ) -> tuple[Optional[str], list[dict]]:
        """Fuzzy search restaurants by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, dining_data = result

        results_with_score = []
        for building in dining_data:
            for restaurant in building["restaurants"]:
                similarity = fuzz.partial_ratio(query, restaurant["name"])
                if similarity >= FUZZY_SEARCH_THRESHOLD:
                    results_with_score.append((similarity, restaurant))

        results_with_score.sort(key=lambda x: x[0], reverse=True)
        return commit_hash, [restaurant for _, restaurant in results_with_score]


# Global service instance
dining_service = DiningService()
