"""
Courses domain service.

Handles course data fetching, processing, and querying.
"""

import operator
from typing import Optional

from data_api.data.manager import nthudata
from data_api.domain.courses.models import Conditions, CourseData


class CoursesService:
    """Service for course data operations."""

    def __init__(self) -> None:
        self.course_data: list[CourseData] = []
        self.last_commit_hash: Optional[str] = None

    async def update_data(self) -> None:
        """Update course data from remote source."""
        result = await nthudata.get("courses.json")
        if result is None:
            print("Warning: Could not fetch courses.json, keeping existing data")
            return

        self.last_commit_hash, raw_data = result

        # Convert dicts to CourseData objects
        self.course_data = list(map(CourseData.from_dict, raw_data))

    def list_selected_fields(self, field: str) -> list[str]:
        """Return all non-empty values for a specific field."""
        fields_set = {
            getattr(course, field).strip()
            for course in self.course_data
            if getattr(course, field).strip()
        }
        return list(fields_set)

    def list_credit(self, credit: float, op: str = "") -> list[CourseData]:
        """Filter courses by credit with operator."""
        ops = {
            "gt": operator.gt,
            "lt": operator.lt,
            "gte": operator.ge,
            "lte": operator.le,
            "eq": operator.eq,
            "": operator.eq,
        }
        cmp_op = ops.get(op, operator.eq)
        return [
            course
            for course in self.course_data
            if cmp_op(float(course.credit) if course.credit else 0, credit)
        ]

    def query(self, conditions: Conditions) -> list[CourseData]:
        """Search all courses matching conditions."""
        return [course for course in self.course_data if conditions.accept(course)]


# Global service instance
courses_service = CoursesService()
