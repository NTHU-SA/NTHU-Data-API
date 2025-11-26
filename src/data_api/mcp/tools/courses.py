"""Course search MCP tool."""

from typing import Optional

from data_api.domain.courses import models as courses_models
from data_api.domain.courses import services as courses_services
from data_api.mcp.server import mcp


async def _search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Search for courses at NTHU.

    Args:
        keyword: Search in course titles (Chinese or English).
        teacher: Teacher name to search for.
        course_id: Specific course ID to look up.
        limit: Maximum number of results to return (default 20).

    Returns:
        Dictionary with matching courses.
    """
    # Build search conditions
    conditions_list = []

    if keyword:
        # Search both Chinese and English titles
        conditions_list.append(
            [
                {"row_field": "chinese_title", "matcher": keyword, "regex_match": True},
                "or",
                {"row_field": "english_title", "matcher": keyword, "regex_match": True},
            ]
        )

    if teacher:
        teacher_cond = {"row_field": "teacher", "matcher": teacher, "regex_match": True}
        if conditions_list:
            conditions_list = [conditions_list[0], "and", teacher_cond]
        else:
            conditions_list.append(teacher_cond)

    if course_id:
        id_cond = {"row_field": "id", "matcher": course_id, "regex_match": True}
        if conditions_list:
            conditions_list = [conditions_list[0], "and", id_cond]
        else:
            conditions_list.append(id_cond)

    if not conditions_list:
        # Return all courses if no filter specified
        courses = courses_services.courses_service.course_data[:limit]
    else:
        # Build and execute query
        if len(conditions_list) == 1:
            query_target = conditions_list[0]
        else:
            query_target = conditions_list

        condition = courses_models.Conditions(list_build_target=query_target)
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
    description="Search for courses at NTHU. "
    "Use this to find courses by name, teacher, time, or other criteria."
)
async def search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Search for courses at NTHU."""
    return await _search_courses(keyword, teacher, course_id, limit)
