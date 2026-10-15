"""Normalized, independently cached course snapshots for each published semester."""

from pydantic import TypeAdapter

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.data.nthudata import (
    DatasetState,
    FetchFailure,
    Freshness,
    JsonData,
    NTHUDataManager,
    Snapshot,
)
from data_api.domain.courses.models import Conditions
from data_api.models.courses import CourseCatalog, CourseData, CourseListName, SemesterCode

LATEST_PATH = "courses/latest.json"
CATALOG_PATH = "courses/sources.json"


class UnknownSemester(Exception):
    """A well-formed semester absent from a verified published catalog."""


def prepare_courses(raw: JsonData, semester: str | None = None) -> list[CourseData]:
    if not isinstance(raw, list):
        raise FetchFailure("payload_type")
    courses = TypeAdapter(list[CourseData]).validate_python(raw, strict=True)
    ids = [course.id for course in courses]
    if len(ids) != len(set(ids)) or (
        semester is not None and any(course.semester_code != semester for course in courses)
    ):
        raise FetchFailure("validation")
    return courses


def prepare_catalog(raw: JsonData) -> list[str]:
    return CourseCatalog.model_validate(raw, strict=True).semesters


class CoursesService:
    def __init__(self, manager: NTHUDataManager = nthudata) -> None:
        self.manager = manager
        self.state = manager.register(LATEST_PATH, prepare_courses)
        self.catalog_state = manager.register(CATALOG_PATH, prepare_catalog)
        self._semesters: dict[str, DatasetState[list[CourseData]]] = {}

    async def get_semesters(self) -> Snapshot[list[str]]:
        return await self.manager.get_snapshot(CATALOG_PATH, self.catalog_state)

    async def get_snapshot(self, semester: str | None = None) -> Snapshot[list[CourseData]]:
        if semester is None:
            return await self.manager.get_snapshot(LATEST_PATH, self.state)
        semester = TypeAdapter(SemesterCode).validate_python(semester, strict=True)
        catalog = await self.get_semesters()
        if semester not in catalog.data:
            if self.catalog_state.freshness != Freshness.CURRENT:
                raise DataNotAvailableException("Semester catalog temporarily unavailable.")
            raise UnknownSemester("Semester is not published.")
        path = f"courses/semesters/{semester}.json"
        if semester not in self._semesters:
            self._semesters[semester] = self.manager.register(
                path, lambda raw: prepare_courses(raw, semester)
            )
        return await self.manager.get_snapshot(path, self._semesters[semester])

    @staticmethod
    def query(
        courses: list[CourseData],
        conditions: Conditions,
        course_type: CourseListName | None = None,
    ) -> list[CourseData]:
        return [
            course
            for course in courses
            if conditions.accept(course)
            and (
                course_type is None
                or (
                    course_type == CourseListName.microcredits
                    and course.credits is not None
                    and not course.credits.is_integer()
                )
                or (course_type == CourseListName.xclass and "X-Class" in course.note)
            )
        ]


courses_service = CoursesService()
