"""
Departments domain service.

Handles department and personnel directory data.
"""

from typing import Optional, Union

from data_api.data.manager import nthudata
from thefuzz import fuzz

JSON_PATH = "directory.json"
FUZZY_SEARCH_THRESHOLD_DEPT = 60
FUZZY_SEARCH_THRESHOLD_PERSON = 70


class DepartmentsService:
    """Service for department directory operations."""

    async def get_all_departments(self) -> tuple[Optional[str], list[dict]]:
        """Get all departments."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []
        return result

    async def fuzzy_search_departments_and_people(
        self, query: str
    ) -> tuple[Optional[str], dict[str, list]]:
        """Fuzzy search departments and people."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, {"departments": [], "people": []}

        commit_hash, directory_data = result

        dept_results = []
        person_results = []

        for department in directory_data:
            # Search departments
            dept_similarity = fuzz.partial_ratio(query, department["name"])
            if dept_similarity >= FUZZY_SEARCH_THRESHOLD_DEPT:
                dept_results.append((dept_similarity, department))

            # Search people in this department
            for person in department.get("people", []):
                person_similarity = fuzz.partial_ratio(query, person["name"])
                if person_similarity >= FUZZY_SEARCH_THRESHOLD_PERSON:
                    person_results.append((person_similarity, person))

        dept_results.sort(key=lambda x: x[0], reverse=True)
        person_results.sort(key=lambda x: x[0], reverse=True)

        return commit_hash, {
            "departments": [dept for _, dept in dept_results],
            "people": [person for _, person in person_results],
        }


# Global service instance
departments_service = DepartmentsService()
