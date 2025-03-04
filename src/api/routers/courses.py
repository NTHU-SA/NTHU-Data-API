from contextlib import asynccontextmanager

from fastapi import APIRouter, Body, Depends, FastAPI, Query, Request, Response

from src.api import schemas
from src.api.models.courses import Conditions, Processor

courses = Processor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 的生命週期管理器，用於在應用啟動時更新公車資料。"""
    global courses

    # tasks when app starts
    await courses.update_data()
    yield
    # tasks when app stops


router = APIRouter(lifespan=lifespan)


async def add_custom_header(response: Response):
    """添加 X-Data-Commit-Hash 標頭。

    Args:
        response: FastAPI 的 Response 對象。
    """

    response.headers["X-Data-Commit-Hash"] = str(courses.last_commit_hash)


@router.get(
    "/",
    response_model=list[schemas.courses.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def get_all_courses_list(
    response: Response,
):
    """
    取得所有課程。
    """
    result = courses.course_data
    response.headers["X-Total-Count"] = str(len(result))
    response.headers["X-Data-Commit-Hash"] = str(courses.last_commit_hash)
    return result


@router.get(
    "/lists/{list_name}",
    response_model=list[schemas.courses.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def get_courses_list(
    list_name: schemas.courses.CourseListName,
    response: Response,
) -> list[schemas.courses.CourseData]:
    """
    取得指定類型的課程列表。
    """
    match list_name:
        case "microcredits":
            condition = Conditions("credit", "[0-9].[0-9]", True)
        case "xclass":
            condition = Conditions("note", "X-Class", True)
    result = courses.query(condition)
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get(
    "/search",
    response_model=list[schemas.courses.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def search_by_field_and_value(
    request: Request,
    response: Response,
    chinese_title: str = Query(None, description="中文標題搜尋", example="微積分"),
    english_title: str = Query(None, description="英文標題搜尋"),
    teacher: str = Query(None, description="教師搜尋"),
    department: str = Query(None, description="開課系所搜尋"),
    credit: str = Query(None, description="學分搜尋", example="3"),
    note: str = Query(None, description="備註搜尋"),
    class_room_and_time: str = Query(None, description="教室與時間搜尋"),
    id: str = Query(None, description="課程ID搜尋"),
    code: str = Query(None, description="課程代碼搜尋"),
):
    """
    根據提供的欄位和值搜尋課程。
    可以直接使用欄位名稱作為查詢參數，例如：
    /search?chinese_title=產業.+生涯&english_title=...
    """
    conditions = {}
    query_params = request.query_params  # 從 Request 物件取得查詢參數

    for field_name in schemas.courses.CourseFieldName:
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
            final_condition = Conditions(list_build_target=combined_condition)
        else:
            final_condition = Conditions(list_build_target=condition_list)
        result = courses.query(final_condition)
    else:
        # 沒有條件時，回傳空列表
        result = []

    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.post(
    "/search",
    response_model=list[schemas.courses.CourseData],
    dependencies=[Depends(add_custom_header)],
)
async def get_courses_by_condition(
    query_condition: (
        schemas.courses.CourseQueryCondition | schemas.courses.CourseCondition
    ) = Body(
        openapi_examples={
            "normal_1": {
                "summary": "單一搜尋條件",
                "description": "只使用單一搜尋條件，類似於 GET 方法",
                "value": {
                    "row_field": "chinese_title",
                    "matcher": "數統導論",
                    "regex_match": True,
                },
            },
            "normal_2": {
                "summary": "兩個搜尋條件",
                "description": "使用兩個搜尋條件，例如：黃姓老師 或 孫姓老師開設的課程",
                "value": [
                    {
                        "row_field": "teacher",
                        "matcher": "黃",
                        "regex_match": True,
                    },
                    "or",
                    {
                        "row_field": "teacher",
                        "matcher": "孫",
                        "regex_match": True,
                    },
                ],
            },
            "normal_nested": {
                "summary": "多層搜尋條件",
                "description": "使用巢狀搜尋條件，例如：(3學分的課程) 且 ((統計所 或 數學系開設的課程) 且 (開課時間是T3T4 或 開課時間是R3R4))",
                "value": [
                    {"row_field": "credit", "matcher": "3", "regex_match": True},
                    "and",
                    [
                        [
                            {"row_field": "id", "matcher": "STAT", "regex_match": True},
                            "or",
                            {"row_field": "id", "matcher": "MATH", "regex_match": True},
                        ],
                        "and",
                        [
                            {
                                "row_field": "class_room_and_time",
                                "matcher": "T3T4",
                                "regex_match": True,
                            },
                            "or",
                            {
                                "row_field": "class_room_and_time",
                                "matcher": "R3R4",
                                "regex_match": True,
                            },
                        ],
                    ],
                ],
            },
        }
    ),
):
    """
    根據條件取得課程。
    """
    if type(query_condition) is schemas.courses.CourseCondition:
        condition = Conditions(
            query_condition.row_field.value,
            query_condition.matcher,
            query_condition.regex_match,
        )
    elif type(query_condition) is schemas.courses.CourseQueryCondition:
        # 設定 mode="json" 是為了讓 dump 出來的內容不包含 python 的實體 (instance)
        condition = Conditions(
            list_build_target=query_condition.model_dump(mode="json")
        )
    result = courses.query(condition)
    return result
