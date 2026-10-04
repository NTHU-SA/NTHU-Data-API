"""
Departments domain service.

Handles department and personnel directory data.
"""

from typing import Optional

from thefuzz import fuzz

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata

JSON_PATH = "directory.json"
FUZZY_SEARCH_THRESHOLD_DEPT = 80
FUZZY_SEARCH_THRESHOLD_PERSON = 80
FUZZY_SEARCH_THRESHOLD_PERSON_TITLE = 90


def _person_match_score(query: str, person: dict) -> int:
    name_score = fuzz.partial_ratio(query, person["name"])
    if name_score >= FUZZY_SEARCH_THRESHOLD_PERSON:
        return name_score
    title_score = fuzz.partial_ratio(query, person.get("title") or "")
    return title_score if title_score >= FUZZY_SEARCH_THRESHOLD_PERSON_TITLE else 0


class DepartmentsService:
    """Service for department directory operations."""

    async def get_all_departments(self) -> tuple[Optional[str], list[dict]]:
        """Get all departments."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")
        return result

    async def get_directory(self, query: str | None = None) -> tuple[Optional[str], list[dict]]:
        """Return matching departments, retaining only matching people when needed."""
        commit_hash, directory_data = await self.get_all_departments()
        if not query:
            return commit_hash, directory_data

        results = []
        for department in directory_data:
            department_score = fuzz.partial_ratio(query, department["name"])
            if department_score >= FUZZY_SEARCH_THRESHOLD_DEPT:
                results.append((department_score, department))
                continue

            details = department.get("details", {})
            matching_people = [
                (score, person)
                for person in details.get("people", [])
                if (score := _person_match_score(query, person))
            ]
            if matching_people:
                results.append(
                    (
                        max(score for score, _ in matching_people),
                        {
                            **department,
                            "details": {
                                **details,
                                "people": [person for _, person in matching_people],
                            },
                        },
                    )
                )

        results.sort(key=lambda item: item[0], reverse=True)
        return commit_hash, [department for _, department in results]

    async def fuzzy_search_departments_and_people(
        self, query: str
    ) -> tuple[Optional[str], dict[str, list]]:
        """Fuzzy search departments and people."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")

        commit_hash, directory_data = result

        dept_results = []
        person_results = []

        for department in directory_data:
            # Search departments
            dept_similarity = fuzz.partial_ratio(query, department["name"])
            if dept_similarity >= FUZZY_SEARCH_THRESHOLD_DEPT:
                dept_results.append((dept_similarity, department))

            # Search people in this department
            people = department.get("details", {}).get("people", [])
            for person in people:
                if score := _person_match_score(query, person):
                    person_results.append((score, person))

        dept_results.sort(key=lambda x: x[0], reverse=True)
        person_results.sort(key=lambda x: x[0], reverse=True)

        return commit_hash, {
            "departments": [dept for _, dept in dept_results],
            "people": [person for _, person in person_results],
        }


# Global service instance
departments_service = DepartmentsService()
