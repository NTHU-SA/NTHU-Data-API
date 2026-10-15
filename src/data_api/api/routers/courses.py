"""Courses router."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from data_api.api.schemas import courses as schemas
from data_api.api.schemas.errors import VALIDATION_ERROR_RESPONSES
from data_api.api.schemas.responses import COUNTED_SNAPSHOT_RESPONSES
from data_api.domain.courses import models
from data_api.runtime import get_runtime

router = APIRouter(responses={**COUNTED_SNAPSHOT_RESPONSES, **VALIDATION_ERROR_RESPONSES})
COURSE_QUERY_ERROR_RESPONSES = {
    422: {
        **VALIDATION_ERROR_RESPONSES[422],
        "description": "Invalid condition grammar, query limits or regular expression",
    }
}


async def add_custom_header(response: Response):
    """Add X-Data-Commit-Hash header."""
    service = get_runtime().courses
    await service.update_data()
    if service.last_commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = service.last_commit_hash


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
) -> list[models.CourseData]:
    condition = models.Conditions(list_build_target=[])
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
    if course_type is not None:
        condition &= _course_type_condition(course_type)

    result = get_runtime().courses.query(condition)
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


@router.post(
    "/query",
    response_model=list[schemas.CourseData],
    dependencies=[Depends(add_custom_header)],
    operation_id="queryCourses",
    responses=COURSE_QUERY_ERROR_RESPONSES,
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
    非空陣列必須依條件、and/or 運算子、條件交替排列，並由左至右計算；空陣列符合全部課程。
    最多 32 層陣列及 1024 個節點（陣列、條件物件、運算子）；無效文法或超過上限回傳 HTTP 422。
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
    result = get_runtime().courses.query(condition)
    response.headers["X-Total-Count"] = str(len(result))
    return result
