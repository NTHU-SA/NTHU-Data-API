from fastapi import APIRouter, Body, HTTPException, Path, Query, Response

from src.api import constant, schemas
from src.api.models.courses import Conditions, Processor

router = APIRouter()
courses = Processor(semester=constant.courses.DEFAULT_SEMESTER)


@router.get("/", response_model=list[schemas.courses.CourseData])
async def get_all_courses_list(
    response: Response,
    semester: schemas.courses.CourseSemester = Query(
        constant.courses.DEFAULT_SEMESTER, example="11210", description="學期代碼"
    ),
    limits: int = constant.general.LIMITS_QUERY,
):
    """
    取得所有課程。
    """
    courses.set_semester(semester)
    result = courses.course_data[:limits]
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get("/fields/info", response_model=dict[str, str])
async def get_all_fields_list_info():
    """
    取得所有欄位的資訊。
    """
    return {
        "id": "科號",
        "chinese_title": "課程中文名稱",
        "english_title": "課程英文名稱",
        "credit": "學分數",
        "size_limit": "人限：若為空字串表示無人數限制",
        "freshman_reservation": "新生保留人數：若為0表示無新生保留人數",
        "object": "通識對象：[代碼說明(課務組)](https://curricul.site.nthu.edu.tw/p/404-1208-11133.php)",
        "ge_type": "通識類別",
        "language": '授課語言："中"、"英"',
        "note": "備註",
        "suspend": '停開註記："停開"或空字串',
        "class_room_and_time": "教室與上課時間：一間教室對應一個上課時間，中間以tab分隔；多個上課教室以new line字元分開",
        "teacher": "授課教師：多位教師授課以new line字元分開；教師中英文姓名以tab分開",
        "prerequisite": "擋修說明：會有html entities",
        "limit_note": "課程限制說明",
        "expertise": "第一二專長對應：對應多個專長用tab字元分隔",
        "program": "學分學程對應：用半形/分隔",
        "no_extra_selection": "不可加簽說明",
        "required_optional_note": "必選修說明：多個必選修班級用tab字元分隔",
    }


@router.get("/fields/{field_name}", response_model=list[str])
async def get_selected_fields_list(
    field_name: schemas.courses.CourseFieldName = Path(
        ..., example="id", description="欄位名稱"
    ),
    semester: schemas.courses.CourseSemester = Query(
        constant.courses.DEFAULT_SEMESTER, example="11210", description="學期代碼"
    ),
    limits: int = constant.general.LIMITS_QUERY,
):
    """
    取得指定欄位的列表。
    """
    courses.set_semester(semester)
    result = courses.list_selected_fields(field_name)[:limits]
    return result


@router.get(
    "/fields/{field_name}/{value}", response_model=list[schemas.courses.CourseData]
)
async def get_selected_field_and_value_data(
    field_name: schemas.courses.CourseFieldName = Path(
        ..., example="chinese_title", description="搜尋的欄位名稱"
    ),
    value: str = Path(..., example="產業創新與生涯探索", description="搜尋的值"),
    semester: schemas.courses.CourseSemester = Query(
        constant.courses.DEFAULT_SEMESTER, example="11210", description="學期代碼"
    ),
    limits: int = constant.general.LIMITS_QUERY,
):
    """
    取得指定欄位滿足搜尋值的課程列表。
    """
    courses.set_semester(semester)
    condition = Conditions(field_name, value, False)
    result = courses.query(condition)[:limits]
    return result


@router.get("/lists/{list_name}", response_model=list[schemas.courses.CourseData])
async def get_courses_list(
    list_name: schemas.courses.CourseListName,
    response: Response,
    semester: schemas.courses.CourseSemester = Query(
        constant.courses.DEFAULT_SEMESTER, example="11210", description="學期代碼"
    ),
    limits: int = constant.general.LIMITS_QUERY,
) -> list[schemas.courses.CourseData]:
    """
    取得指定類型的課程列表。
    """
    courses.set_semester(semester)
    if list_name == "16weeks":
        condition = Conditions("note", "16週課程", True)
    elif list_name == "microcredits":
        condition = Conditions("credit", "[0-9].[0-9]", True)
    elif list_name == "xclass":
        condition = Conditions("note", "X-Class", True)
    else:
        raise HTTPException(status_code=400, detail="Invalid list name")
    result = courses.query(condition)[:limits]
    response.headers["X-Total-Count"] = str(len(result))
    return result


@router.get("/searches", response_model=list[schemas.courses.CourseData])
async def search_by_field_and_value(
    field: schemas.courses.CourseFieldName = Query(
        ...,
        example=schemas.courses.CourseFieldName.chinese_title,
        description="搜尋的欄位名稱",
    ),
    value: str = Query(..., example="產業.+生涯", description="搜尋的值（可以使用 Regex，正則表達式）"),
    semester: schemas.courses.CourseSemester = Query(
        constant.courses.DEFAULT_SEMESTER, example="11210", description="學期代碼"
    ),
    limits: int = constant.general.LIMITS_QUERY,
):
    """
    取得指定欄位滿足搜尋值的課程列表。
    """
    courses.set_semester(semester)
    condition = Conditions(field, value, True)
    result = courses.query(condition)[:limits]
    return result


@router.post("/searches", response_model=list[schemas.courses.CourseData])
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
    semester: schemas.courses.CourseSemester = Query(
        constant.courses.DEFAULT_SEMESTER, example="11210", description="學期代碼"
    ),
    limits: int = constant.general.LIMITS_QUERY,
):
    """
    根據條件取得課程。
    """
    courses.set_semester(semester)
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
    result = courses.query(condition)[:limits]
    return result
