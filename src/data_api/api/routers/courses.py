"""Courses router."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from data_api.api.schemas import courses as schemas
from data_api.domain.courses import models, services

router = APIRouter()


async def add_custom_header(response: Response):
    """Add X-Data-Commit-Hash header."""
    await services.courses_service.update_data()
    if services.courses_service.last_commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = services.courses_service.last_commit_hash


@router.get(
    "/",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="getAllCourses",
)
async def get_all_courses(response: Response):
    """
    取得所有課程。
    資料來源：[教務處課務組/JSON格式下載](https://curricul.site.nthu.edu.tw/p/406-1208-111356,r7883.php?Lang=zh-tw)
    """
    result = services.courses_service.course_data
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get(
    "/search",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="searchCoursesByFieldAndValue",
    responses={422: {"description": "Invalid query parameter or regular expression"}},
)
async def search_courses_by_field_and_value(
    response: Response,
    filters: Annotated[schemas.CourseSearchParams, Query()],
):
    """
    根據提供的欄位和值搜尋課程。
    - 使用欄位名稱作為查詢參數
    - 值使用正則表達式；格式無效時回傳 HTTP 422
    - 例如：/search?chinese_title=產業.+&english_title=...
    """
    conditions = {}
    query_params = filters.model_dump(mode="json", exclude_none=True)

    for field_name in schemas.CourseFieldName:
        field_value = query_params.get(field_name.value)
        if field_value:
            conditions[field_name] = field_value

    if conditions:
        final_condition = models.Conditions(list_build_target=[])
        for name, value in conditions.items():
            try:
                query_condition = schemas.CourseCondition(
                    row_field=name, matcher=value, regex_match=True
                )
            except ValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid regular expression for course field '{name.value}'.",
                ) from exc
            final_condition &= models.Conditions(
                query_condition.row_field.value,
                query_condition.matcher,
                query_condition.regex_match,
            )
        result = services.courses_service.query(final_condition)
    else:
        result = []

    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.post(
    "/search",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="searchCoursesByCondition",
)
async def search_courses_by_condition(
    query_condition: Annotated[
        schemas.CourseQueryCondition | schemas.CourseCondition,
        Body(
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
    ],
):
    """
    進階搜尋，根據條件取得課程。可以使用巢狀條件。
    regex_match 啟用時使用正則表達式，格式無效時回傳 HTTP 422；否則使用完全符合。
    """
    if type(query_condition) is schemas.CourseCondition:
        condition = models.Conditions(
            query_condition.row_field.value,
            query_condition.matcher,
            query_condition.regex_match,
        )
    elif type(query_condition) is schemas.CourseQueryCondition:
        condition = models.Conditions(list_build_target=query_condition.model_dump(mode="json"))
    result = services.courses_service.query(condition)
    return result


@router.get(
    "/lists/{list_name}",
    dependencies=[Depends(add_custom_header)],
    operation_id="listCoursesByType",
)
async def list_courses_by_type(
    list_name: schemas.CourseListName,
    response: Response,
) -> list[schemas.CourseData]:
    """
    取得指定類型的課程列表。
    """
    match list_name:
        case "microcredits":
            condition = models.Conditions("credit", "[0-9].[0-9]", True)
        case "xclass":
            condition = models.Conditions("note", "X-Class", True)
    result = services.courses_service.query(condition)
    response.headers["X-Total-Count"] = str(len(result))
    return result
