"""Courses router."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from data_api.api.schemas import courses as schemas
from data_api.api.schemas.errors import VALIDATION_ERROR_RESPONSES
from data_api.api.schemas.responses import COUNTED_SNAPSHOT_RESPONSES
from data_api.domain.courses import models, services

router = APIRouter(responses={**COUNTED_SNAPSHOT_RESPONSES, **VALIDATION_ERROR_RESPONSES})


async def add_custom_header(response: Response):
    """Add X-Data-Commit-Hash header."""
    await services.courses_service.update_data()
    if services.courses_service.last_commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = services.courses_service.last_commit_hash


def _course_type_condition(course_type: schemas.CourseListName) -> models.Conditions:
    match course_type:
        case schemas.CourseListName.microcredits:
            return models.Conditions("credit", "[0-9].[0-9]", True)
        case schemas.CourseListName.xclass:
            return models.Conditions("note", "X-Class", True)
    raise ValueError(f"Unsupported course type: {course_type}")


def _filter_courses(
    response: Response,
    filters: schemas.CourseSearchParams,
    course_type: schemas.CourseListName | None = None,
    *,
    empty_without_filters: bool = False,
) -> list[models.CourseData]:
    condition = models.Conditions(list_build_target=[])
    has_filters = False
    query_params = filters.model_dump(mode="json", exclude_none=True)
    for field_name in schemas.CourseFieldName:
        field_value = query_params.get(field_name.value)
        if not field_value:
            continue
        try:
            query_condition = schemas.CourseCondition(
                row_field=field_name, matcher=field_value, regex_match=True
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid regular expression for course field '{field_name.value}'.",
            ) from exc
        condition &= models.Conditions(
            query_condition.row_field.value,
            query_condition.matcher,
            query_condition.regex_match,
        )
        has_filters = True
    if course_type is not None:
        condition &= _course_type_condition(course_type)
        has_filters = True

    result = (
        []
        if empty_without_filters and not has_filters
        else services.courses_service.query(condition)
    )
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get(
    "",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="getCourses",
)
async def get_courses(
    response: Response,
    filters: Annotated[schemas.CourseGetParams, Query()],
):
    """
    取得課程；未提供篩選條件時回傳所有課程。
    欄位值使用正則表達式，所有欄位與 type 條件以 AND 組合。
    type 可為 microcredits 或 xclass；無效類型或正則表達式回傳 HTTP 422。
    資料來源：[教務處課務組/JSON格式下載](https://curricul.site.nthu.edu.tw/p/406-1208-111356,r7883.php?Lang=zh-tw)
    """
    return _filter_courses(response, filters, filters.type)


@router.get(
    "/",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="getAllCourses",
    deprecated=True,
)
async def get_all_courses(response: Response):
    """
    已棄用，請改用 GET /courses。此端點仍回傳所有課程。
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
    deprecated=True,
)
async def search_courses_by_field_and_value(
    response: Response,
    filters: Annotated[schemas.CourseSearchParams, Query()],
):
    """
    已棄用，請改用 GET /courses。未提供有效篩選條件時仍回傳空陣列。
    根據提供的欄位和值搜尋課程。
    - 使用欄位名稱作為查詢參數
    - 值使用正則表達式；格式無效時回傳 HTTP 422
    - 例如：/search?chinese_title=產業.+&english_title=...
    """
    return _filter_courses(response, filters, empty_without_filters=True)


@router.post(
    "/query",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="queryCourses",
)
@router.post(
    "/search",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="searchCoursesByCondition",
    deprecated=True,
    description="已棄用，請改用 POST /courses/query。支援相同的單一與巢狀 AND/OR 條件。",
)
async def search_courses_by_condition(
    response: Response,
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
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get(
    "/lists/{list_name}",
    dependencies=[Depends(add_custom_header)],
    operation_id="listCoursesByType",
    deprecated=True,
)
async def list_courses_by_type(
    list_name: schemas.CourseListName,
    response: Response,
) -> list[schemas.CourseData]:
    """
    已棄用，請改用 GET /courses?type={list_name}。
    取得指定類型的課程列表。
    """
    condition = _course_type_condition(list_name)
    result = services.courses_service.query(condition)
    response.headers["X-Total-Count"] = str(len(result))
    return result
