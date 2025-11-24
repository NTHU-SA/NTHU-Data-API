"""Courses router."""

from fastapi import APIRouter, Body, Depends, Query, Request, Response

from data_api.api.schemas import courses as schemas
from data_api.domain.courses import models, services

router = APIRouter()


async def add_custom_header(response: Response):
    """Add X-Data-Commit-Hash header."""
    response.headers["X-Data-Commit-Hash"] = str(services.courses_service.last_commit_hash)


@router.get(
    "/",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def get_all_courses(response: Response):
    """
    Get all courses.
    Data source: Academic Affairs Office
    """
    result = services.courses_service.course_data
    response.headers["X-Total-Count"] = str(len(result))
    response.headers["X-Data-Commit-Hash"] = str(services.courses_service.last_commit_hash)
    return result


@router.get(
    "/search",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def search_courses_by_field_and_value(
    request: Request,
    response: Response,
    id: str = Query(None, description="課號"),
    chinese_title: str = Query(None, description="課程中文名稱"),
    english_title: str = Query(None, description="課程英文名稱"),
    credit: str = Query(None, description="學分數"),
    size_limit: str = Query(None, description="人限"),
    freshman_reservation: str = Query(None, description="新生保留人數"),
    object: str = Query(None, description="通識對象"),
    ge_type: str = Query(None, description="通識類別"),
    language: schemas.CourseLanguage = Query(None, description="授課語言"),
    note: str = Query(None, description="備註"),
    suspend: str = Query(None, description="停開註記"),
    class_room_and_time: str = Query(None, description="教室與上課時間"),
    teacher: str = Query(None, description="授課教師"),
    prerequisite: str = Query(None, description="擋修說明"),
    limit_note: str = Query(None, description="課程限制說明"),
    expertise: str = Query(None, description="第一二專長對應"),
    program: str = Query(None, description="學分學程對應"),
    no_extra_selection: str = Query(None, description="不可加簽說明"),
    required_optional_note: str = Query(None, description="必選修說明"),
):
    """
    Search courses by field and value.
    """
    conditions = {}
    query_params = request.query_params

    for field_name in schemas.CourseFieldName:
        field_value = query_params.get(field_name.value)
        if field_value:
            conditions[field_name] = field_value

    if conditions:
        condition_list = []
        for name, value in conditions.items():
            condition_list.append(
                {
                    "row_field": name.value,
                    "matcher": value,
                    "regex_match": True,
                }
            )
        if len(condition_list) > 1:
            combined_condition = []
            for i in range(len(condition_list)):
                combined_condition.append(condition_list[i])
                if i < len(condition_list) - 1:
                    combined_condition.append("and")
            final_condition = models.Conditions(list_build_target=combined_condition)
        else:
            final_condition = models.Conditions(list_build_target=condition_list)
        result = services.courses_service.query(final_condition)
    else:
        result = []

    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.post(
    "/search",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def search_courses_by_condition(
    query_condition: schemas.CourseQueryCondition | schemas.CourseCondition = Body(
        openapi_examples={
            "normal_1": {
                "summary": "單一搜尋條件",
                "value": {
                    "row_field": "chinese_title",
                    "matcher": "數統導論",
                    "regex_match": True,
                },
            },
            "normal_2": {
                "summary": "兩個搜尋條件",
                "value": [
                    {"row_field": "teacher", "matcher": "黃", "regex_match": True},
                    "or",
                    {"row_field": "teacher", "matcher": "孫", "regex_match": True},
                ],
            },
        }
    ),
):
    """Search courses by complex conditions."""
    if type(query_condition) is schemas.CourseCondition:
        condition = models.Conditions(
            query_condition.row_field.value,
            query_condition.matcher,
            query_condition.regex_match,
        )
    elif type(query_condition) is schemas.CourseQueryCondition:
        condition = models.Conditions(
            list_build_target=query_condition.model_dump(mode="json")
        )
    result = services.courses_service.query(condition)
    return result


@router.get(
    "/lists/{list_name}",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def list_courses_by_type(
    list_name: schemas.CourseListName,
    response: Response,
) -> list[schemas.CourseData]:
    """Get courses by predefined list type."""
    match list_name:
        case "microcredits":
            condition = models.Conditions("credit", "[0-9].[0-9]", True)
        case "xclass":
            condition = models.Conditions("note", "X-Class", True)
    result = services.courses_service.query(condition)
    response.headers["X-Total-Count"] = str(len(result))
    return result
