"""Latest and semester-specific normalized course queries."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from data_api.api.schemas import courses as schemas
from data_api.api.schemas.errors import VALIDATION_ERROR_RESPONSES, ErrorResponse
from data_api.api.schemas.responses import COUNTED_SNAPSHOT_RESPONSES
from data_api.data.nthudata import Snapshot
from data_api.domain.courses.models import Conditions
from data_api.domain.courses.services import UnknownSemester
from data_api.models.courses import SemesterCode
from data_api.runtime import get_runtime

router = APIRouter(responses={**COUNTED_SNAPSHOT_RESPONSES, **VALIDATION_ERROR_RESPONSES})
COURSE_QUERY_ERROR_RESPONSES = {
    422: {
        **VALIDATION_ERROR_RESPONSES[422],
        "description": "Invalid condition grammar, matcher types, query limits or regular expression",
    }
}
SEMESTER_ERRORS = {404: {"model": ErrorResponse, "description": "Semester is not published"}}


async def latest_snapshot() -> Snapshot[list[schemas.CourseData]]:
    return await get_runtime().courses.get_snapshot()


async def semester_snapshot(semester: SemesterCode) -> Snapshot[list[schemas.CourseData]]:
    try:
        return await get_runtime().courses.get_snapshot(semester)
    except UnknownSemester as exc:
        raise HTTPException(404, detail="Semester is not published.") from exc


LatestSnapshot = Annotated[Snapshot[list[schemas.CourseData]], Depends(latest_snapshot)]
SemesterSnapshot = Annotated[Snapshot[list[schemas.CourseData]], Depends(semester_snapshot)]
CourseFilters = Annotated[schemas.CourseGetParams, Query()]
CourseQuery = Annotated[schemas.CourseQueryCondition | schemas.CourseCondition, Body()]


def counted_response[T](
    response: Response, snapshot: Snapshot[list[T]], result: list[T]
) -> list[T]:
    response.headers["X-Total-Count"] = str(len(result))
    if snapshot.version is not None:
        response.headers["X-Data-Commit-Hash"] = snapshot.version
    return result


def filter_courses(
    response: Response,
    snapshot: Snapshot[list[schemas.CourseData]],
    filters: schemas.CourseGetParams,
) -> list[schemas.CourseData]:
    condition = Conditions(list_build_target=[])
    for field_name, value in filters.model_dump(
        mode="json", by_alias=True, exclude_none=True, exclude={"type"}
    ).items():
        if value == "":
            continue
        try:
            query = schemas.CourseCondition(
                row_field=field_name, matcher=value, regex_match=isinstance(value, str)
            )
        except ValidationError as exc:
            raise HTTPException(
                422, detail=f"Invalid regular expression for course field '{field_name}'."
            ) from exc
        condition &= Conditions(query.row_field, query.matcher, query.regex_match)
    result = get_runtime().courses.query(snapshot.data, condition, filters.type)
    return counted_response(response, snapshot, result)


def query_courses(
    response: Response,
    snapshot: Snapshot[list[schemas.CourseData]],
    query: schemas.CourseQueryCondition | schemas.CourseCondition,
) -> list[schemas.CourseData]:
    body = query.model_dump(mode="json")
    condition = Conditions(list_build_target=[body] if isinstance(body, dict) else body)
    result = get_runtime().courses.query(snapshot.data, condition)
    return counted_response(response, snapshot, result)


@router.get("", response_model=list[schemas.CourseData], operation_id="getCourses")
async def get_courses(response: Response, filters: CourseFilters, snapshot: LatestSnapshot):
    """查詢最新課程。文字欄位使用 regex，數值與布林精確比對；所有條件以 AND 組合。"""
    return filter_courses(response, snapshot, filters)


@router.get("/semesters", response_model=list[SemesterCode], operation_id="getCourseSemesters")
async def get_semesters(response: Response):
    """列出已公布的學期碼，由新到舊排序。"""
    snapshot = await get_runtime().courses.get_semesters()
    return counted_response(response, snapshot, snapshot.data)


@router.post(
    "/query",
    response_model=list[schemas.CourseData],
    operation_id="queryCourses",
    responses=COURSE_QUERY_ERROR_RESPONSES,
)
async def search_courses_by_condition(
    response: Response, query_condition: CourseQuery, snapshot: LatestSnapshot
):
    """進階搜尋最新課程。條件以 and/or 交替並由左至右計算，支援巢狀陣列。

    空陣列符合全部；最多 32 層與 1024 節點。matcher 使用欄位的原生型別，
    regex_match 只適用文字，預設為 false。陣列葉節點採任一元素符合。
    """
    return query_courses(response, snapshot, query_condition)


@router.get(
    "/{semester}",
    response_model=list[schemas.CourseData],
    operation_id="getSemesterCourses",
    responses=SEMESTER_ERRORS,
)
async def get_semester_courses(
    response: Response, filters: CourseFilters, snapshot: SemesterSnapshot
):
    """查詢指定學期課程，篩選方式與 GET /courses 相同，不自動改查其他學期。"""
    return filter_courses(response, snapshot, filters)


@router.post(
    "/{semester}/query",
    response_model=list[schemas.CourseData],
    operation_id="querySemesterCourses",
    responses={**SEMESTER_ERRORS, **COURSE_QUERY_ERROR_RESPONSES},
)
async def query_semester_courses(
    response: Response, query_condition: CourseQuery, snapshot: SemesterSnapshot
):
    """進階搜尋指定學期，條件文法與 POST /courses/query 相同。"""
    return query_courses(response, snapshot, query_condition)
