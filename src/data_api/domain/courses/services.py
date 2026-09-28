"""
Courses domain service.

Handles course data fetching, processing, and querying.
"""

import operator
from typing import Optional

from pydantic import TypeAdapter

from data_api.data.manager import nthudata
from data_api.data.nthudata import FetchFailure, JsonData, NTHUDataManager
from data_api.domain.courses.models import Conditions, CourseData


def prepare_courses(raw: JsonData) -> list[CourseData]:
    from data_api.api.schemas.courses import CourseData as CourseSchema

    if not isinstance(raw, list):
        raise FetchFailure("payload_type")
    rows = TypeAdapter(list[dict]).validate_python(raw, strict=True)
    courses = [CourseData.from_dict(row) for row in rows]
    for course in courses:
        CourseSchema.model_validate(course, from_attributes=True)
    if any(not course.id.strip() for course in courses):
        raise FetchFailure("validation")
    return courses


class CoursesService:
    """Service for course data operations."""

    def __init__(self, manager: NTHUDataManager = nthudata) -> None:
        self.manager = manager
        self.state = manager.register("courses.json", prepare_courses)
        self.course_data: list[CourseData] = []
        self.last_commit_hash: Optional[str] = None

    async def update_data(self) -> None:
        """Update course data from remote source."""
        snapshot = await self.manager.get_snapshot("courses.json", self.state)
        # No await between these assignments and synchronous queries.
        self.course_data = snapshot.data
        self.last_commit_hash = snapshot.version

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
