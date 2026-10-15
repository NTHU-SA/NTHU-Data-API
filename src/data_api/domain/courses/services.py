"""
Courses domain service.

Handles course data fetching, processing, and querying.
"""

from typing import Optional

from pydantic import TypeAdapter

from data_api.data.manager import nthudata
from data_api.data.nthudata import FetchFailure, JsonData, NTHUDataManager, Snapshot
from data_api.domain.courses.models import Conditions, CourseData


def prepare_courses(raw: JsonData) -> list[CourseData]:
    from data_api.models.courses import CourseData as CourseSchema

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
        self._snapshot: Snapshot[list[CourseData]] | None = None
        self._course_data: list[CourseData] = []
        self.last_commit_hash: Optional[str] = None

    async def update_data(self) -> None:
        """Update course data from remote source."""
        self._snapshot = await self.manager.get_snapshot("courses.json", self.state)
        self.last_commit_hash = self._snapshot.version

    def reset(self) -> None:
        self._snapshot = None
        self._course_data = []
        self.last_commit_hash = None

    @property
    def course_data(self) -> list[CourseData]:
        return self._snapshot.data if self._snapshot is not None else self._course_data

    @course_data.setter
    def course_data(self, value: list[CourseData]) -> None:
        self._snapshot = None
        self._course_data = value

    def query(self, conditions: Conditions) -> list[CourseData]:
        """Search all courses matching conditions."""
        return [course for course in self.course_data if conditions.accept(course)]


# Global service instance
courses_service = CoursesService()
