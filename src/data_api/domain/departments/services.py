"""
Departments domain service.

Handles department and personnel directory data.
"""

from typing import Optional

from thefuzz import fuzz

from data_api.data.manager import nthudata
from data_api.data.nthudata import NTHUDataManager

JSON_PATH = "directory.json"
FUZZY_SEARCH_THRESHOLD_DEPT = 80
FUZZY_SEARCH_THRESHOLD_PERSON = 80
FUZZY_SEARCH_THRESHOLD_PERSON_TITLE = 90


def _department_match_score(query: str, department: dict, fuzzy: bool) -> int:
    if not fuzzy:
        return 100 if query == department["name"] else 0
    score = fuzz.partial_ratio(query, department["name"])
    return score if score >= FUZZY_SEARCH_THRESHOLD_DEPT else 0


def _person_match_score(query: str, person: dict, fuzzy: bool) -> int:
    if not fuzzy:
        return 100 if query == person["name"] or query == person.get("title") else 0
    name_score = fuzz.partial_ratio(query, person["name"])
    if name_score >= FUZZY_SEARCH_THRESHOLD_PERSON:
        return name_score
    title_score = fuzz.partial_ratio(query, person.get("title") or "")
    return title_score if title_score >= FUZZY_SEARCH_THRESHOLD_PERSON_TITLE else 0


class DepartmentsService:
    """Service for department directory operations."""

    def __init__(self, manager: NTHUDataManager = nthudata):
        self.manager = manager

    async def get_all_departments(self) -> tuple[Optional[str], list[dict]]:
        """Get all departments."""
        return await self.manager.get(JSON_PATH)

    async def get_directory(
        self, query: str | None = None, fuzzy: bool = True
    ) -> tuple[Optional[str], list[dict]]:
        """Return matching departments, retaining only matching people when needed."""
        commit_hash, directory_data = await self.get_all_departments()
        if not query:
            return commit_hash, directory_data

        results = []
        for department in directory_data:
            if department_score := _department_match_score(query, department, fuzzy):
                results.append((department_score, department))
                continue

            details = department.get("details", {})
            matching_people = [
                (score, person)
                for person in details.get("people", [])
                if (score := _person_match_score(query, person, fuzzy))
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

    async def search_departments_and_people(
        self, query: str, fuzzy: bool = True
    ) -> tuple[Optional[str], dict[str, list]]:
        """Search departments and people using fuzzy or exact matching."""
        commit_hash, directory_data = await self.manager.get(JSON_PATH)

        dept_results = []
        person_results = []

        for department in directory_data:
            # Search departments
            if dept_similarity := _department_match_score(query, department, fuzzy):
                dept_results.append((dept_similarity, department))

            # Search people in this department
            people = department.get("details", {}).get("people", [])
            for person in people:
                if score := _person_match_score(query, person, fuzzy):
                    person_results.append((score, person))

        dept_results.sort(key=lambda x: x[0], reverse=True)
        person_results.sort(key=lambda x: x[0], reverse=True)

        return commit_hash, {
            "departments": [dept for _, dept in dept_results],
            "people": [person for _, person in person_results],
        }


# Global service instance
departments_service = DepartmentsService()
