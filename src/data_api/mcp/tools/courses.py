"""Course search MCP tool."""

import re
from typing import Annotated, Optional

from fastmcp.exceptions import ToolError
from pydantic import Field, validate_call

from data_api.domain.courses import models as courses_models
from data_api.domain.courses.services import UnknownSemester
from data_api.mcp.server import mcp
from data_api.mcp.tools.result_types import CoursesResult
from data_api.models.courses import SemesterCode
from data_api.runtime import get_runtime

CourseSearchLimit = Annotated[int, Field(ge=1, le=100)]


@validate_call
async def _search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: CourseSearchLimit = 20,
    semester: SemesterCode | None = None,
) -> CoursesResult:
    """
    Search for courses at NTHU.

    Args:
        keyword: Literal, case-sensitive substring in Chinese or English titles.
        teacher: Literal, case-sensitive substring in teacher names.
        course_id: Literal, case-sensitive substring in course IDs.
        limit: Maximum number of results to return (1-100, default 20).
        semester: Published five-digit semester code; omitted means the upstream latest feed.

    All supplied filters are combined with AND.

    Returns:
        Dictionary with matching courses.
    """
    service = get_runtime().courses
    try:
        snapshot = await service.get_snapshot(semester)
    except UnknownSemester as exc:
        raise ToolError("Semester is not published.") from exc
    condition = courses_models.Conditions(list_build_target=[])

    if keyword:
        condition &= courses_models.Conditions(
            "chinese_title", re.escape(keyword), regex_match=True
        ) | courses_models.Conditions("english_title", re.escape(keyword), regex_match=True)

    if teacher:
        teacher_condition = courses_models.Conditions(
            "lecturers.label", re.escape(teacher), regex_match=True
        )
        for field in ("lecturers.name_zh", "lecturers.name_en"):
            teacher_condition |= courses_models.Conditions(
                field, re.escape(teacher), regex_match=True
            )
        condition &= teacher_condition
    if course_id:
        condition &= courses_models.Conditions("id", re.escape(course_id), regex_match=True)

    courses = service.query(snapshot.data, condition)[:limit]

    # Format response
    return {
        "count": len(courses),
        "courses": [course.model_dump(mode="json") for course in courses],
    }


@mcp.tool(
    name="search_courses",
    title="搜尋課程列表",
    description="Search for courses at NTHU by title, teacher, or course ID. "
    "Inputs are literal, case-sensitive substrings, not regular expressions. "
    "All supplied filters must match. Limit must be 1-100 (default 20). "
    "Semester is an optional published five-digit code; omitted means latest. "
    "Returns normalized course fields, including lecturers, meetings and nullable metadata.",
)
async def search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: CourseSearchLimit = 20,
    semester: SemesterCode | None = None,
) -> dict:
    """Search for courses at NTHU."""
    return await _search_courses(keyword, teacher, course_id, limit, semester)
