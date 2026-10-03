"""Course search MCP tool."""

import re
from typing import Annotated, Optional

from pydantic import Field, validate_call

from data_api.domain.courses import models as courses_models
from data_api.domain.courses import services as courses_services
from data_api.mcp.server import mcp

CourseSearchLimit = Annotated[int, Field(ge=1, le=100)]


@validate_call
async def _search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: CourseSearchLimit = 20,
) -> dict:
    """
    Search for courses at NTHU.

    Args:
        keyword: Literal, case-sensitive substring in Chinese or English titles.
        teacher: Literal, case-sensitive substring in teacher names.
        course_id: Literal, case-sensitive substring in course IDs.
        limit: Maximum number of results to return (1-100, default 20).

    All supplied filters are combined with AND.

    Returns:
        Dictionary with matching courses.
    """
    await courses_services.courses_service.update_data()
    condition = courses_models.Conditions(list_build_target=[])

    if keyword:
        condition &= courses_models.Conditions(
            "chinese_title", re.escape(keyword), regex_match=True
        ) | courses_models.Conditions("english_title", re.escape(keyword), regex_match=True)

    for field_name, value in (("teacher", teacher), ("id", course_id)):
        if value:
            condition &= courses_models.Conditions(field_name, re.escape(value), regex_match=True)

    courses = courses_services.courses_service.query(condition)[:limit]

    # Format response
    return {
        "count": len(courses),
        "courses": [
            {
                "id": c.id,
                "chinese_title": c.chinese_title,
                "english_title": c.english_title,
                "teacher": c.teacher,
                "credit": c.credit,
                "time_and_room": c.class_room_and_time,
                "language": c.language.value if hasattr(c.language, "value") else str(c.language),
                "note": c.note if c.note else None,
            }
            for c in courses
        ],
    }


@mcp.tool(
    name="search_courses",
    title="搜尋課程列表",
    description="Search for courses at NTHU by title, teacher, or course ID. "
    "Inputs are literal, case-sensitive substrings, not regular expressions. "
    "All supplied filters must match. Limit must be 1-100 (default 20).",
)
async def search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: CourseSearchLimit = 20,
) -> dict:
    """Search for courses at NTHU."""
    return await _search_courses(keyword, teacher, course_id, limit)
