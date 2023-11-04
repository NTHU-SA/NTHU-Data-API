from enum import Enum
from typing import Optional
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from ..models.courses import Conditions, Processor


class FieldName(str, Enum):
    id = "id"
    chinese_title = "chinese_title"
    english_title = "english_title"
    credit = "credit"
    size_limit = "size_limit"
    freshman_reservation = "freshman_reservation"
    object = "object"
    ge_type = "ge_type"
    language = "language"
    note = "note"
    suspend = "suspend"
    class_room_and_time = "class_room_and_time"
    teacher = "teacher"
    prerequisite = "prerequisite"
    limit_note = "limit_note"
    expertise = "expertise"
    program = "program"
    no_extra_selection = "no_extra_selection"
    required_optional_note = "required_optional_note"


class Language(str, Enum):
    Chinese = "中"
    English = "英"


class Operation(str, Enum):
    GreaterThan = "gt"
    LessThan = "lt"
    GreaterThanOrEqual = "gte"
    LessThanOrEqual = "lte"


class Course(BaseModel):
    id: str = Field(..., description="課號")
    chinese_title: str = Field(..., description="課程中文名稱")
    english_title: str = Field(..., description="課程英文名稱")
    credit: str = Field(..., description="學分數")
    size_limit: str = Field(..., description="人限：若為空字串表示無人數限制")
    freshman_reservation: str = Field(..., description="新生保留人數：若為0表示無新生保留人數")
    object: str = Field(
        ...,
        description="通識對象：[代碼說明(課務組)](https://curricul.site.nthu.edu.tw/p/404-1208-11133.php)",
    )
    ge_type: str = Field(..., description="通識類別")
    language: Language = Field(..., description='授課語言："中"、"英"')
    note: str = Field(..., description="備註")
    suspend: str = Field(..., description='停開註記："停開"或空字串')
    class_room_and_time: str = Field(
        ..., description="教室與上課時間：一間教室對應一個上課時間，中間以tab分隔；多個上課教室以new line字元分開"
    )
    teacher: str = Field(..., description="授課教師：多位教師授課以new line字元分開；教師中英文姓名以tab分開")
    prerequisite: str = Field(..., description="擋修說明：會有html entities")
    limit_note: str = Field(..., description="課程限制說明")
    expertise: str = Field(..., description="第一二專長對應：對應多個專長用tab字元分隔")
    program: str = Field(..., description="學分學程對應：用半形/分隔")
    no_extra_selection: str = Field(..., description="不可加簽說明")
    required_optional_note: str = Field(..., description="必選修說明：多個必選修班級用tab字元分隔")


router = APIRouter(
    prefix="/courses",
    tags=["courses"],
    responses={404: {"description": "Not found"}},
)

courses = Processor(json_path="data/courses/11210.json")


@router.get("/", response_model=list[Course])
async def get_all_courses(limits: int = Query(None, description="最大回傳資料筆數")):
    """
    取得所有課程。
    """
    try:
        result = courses.course_data[:limits]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/fields", response_model=dict[str, str])
async def list_fields():
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
async def list_selected_fields(
    field_name: FieldName = Path(..., description="欄位名稱"),
    limits: int = Query(None, description="最大回傳資料筆數"),
):
    """
    取得指定欄位的列表。
    """
    try:
        result = courses.list_selected_fields(field_name)[:limits]
        return result
    except AttributeError as e:
        raise HTTPException(
            status_code=500, detail=f"The field '{field_name}' is not exist."
        )


@router.get("/fields/{field_name}/{value}", response_model=list[Course])
async def search_by_field_and_value(
    field_name: FieldName = Path(..., description="搜尋的欄位名稱"),
    value: str = Path(..., description="搜尋的值(使用Regex，正則表達式)"),
    limits: int = Query(None, description="最大回傳資料筆數"),
):
    """
    取得指定欄位滿足搜尋值的課程列表。
    """
    try:
        condition = Conditions(field_name, value, True)
        result = courses.query(condition)[:limits]
        return result
    except KeyError as e:
        raise HTTPException(
            status_code=500, detail=f"The field '{field_name}' is not exist."
        )


@router.get("/languages/{language}", response_model=list[Course])
async def search_courses_by_language(
    language: Language = Path(..., description="搜尋的語言"),
    limits: int = Query(None, description="最大回傳資料筆數"),
):
    """
    取得指定語言的課程列表。
    """
    condition = Conditions("language", language, True)
    result = courses.query(condition)[:limits]
    return result


@router.get("/credits/microcredits", response_model=list[Course])
async def search_courses_by_credits(limits: int = Query(None, description="最大回傳資料筆數")):
    """
    取得微學分課程列表。
    """
    condition = Conditions("credit", f"[0-9].[0-9]", True)
    result = courses.query(condition)[:limits]
    return result


@router.get("/durations/16weeks", response_model=list[Course])
async def search_courses_by_duration(limits: int = Query(None, description="最大回傳資料筆數")):
    """
    取得 16 週課程列表。
    """
    condition = Conditions("note", "本課程為16週課程", True)
    result = courses.query(condition)[:limits]
    return result


@router.get("/searches/id/{course_id}", response_model=list[Course])
async def search_courses_by_id(course_id: str = Path(..., description="搜尋的課號")):
    """
    根據課號取得課程。
    """
    if len(course_id) < 7:
        raise HTTPException(
            status_code=400, detail="Bad Request, course id is too short."
        )
    # 課號是 11210AES 520100，但是有些人會用 11210AES520100
    if course_id[-7] != " ":
        course_id = course_id[:-6] + " " + course_id[-6:]
    condition = Conditions("id", course_id, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(status_code=404, detail="There is no course id match.")
    return result


@router.get("/searches/time/{class_time}", response_model=list[Course])
async def search_courses_by_time(
    class_time: str = Path(..., description="搜尋的上課時間"),
    limits: int = Query(None, description="最大回傳資料筆數"),
):
    """
    根據上課時間取得課程，可以用 W1W2 表示星期一第一節到第二節。
    """
    condition = Conditions("class_room_and_time", class_time, True)
    result = courses.query(condition)[:limits]
    if result == []:
        raise HTTPException(status_code=404, detail="There is no course at this time.")
    return result


@router.get("/searches/classroom/{classroom_name}", response_model=list[Course])
async def search_courses_by_classroom(
    classroom_name: str = Path(..., description="搜尋的教室"),
    limits: int = Query(None, description="最大回傳資料筆數"),
):
    """
    根據教室取得課程，可以用中文或英文教室名稱，也可以使用系館代碼。
    """
    condition = Conditions("class_room_and_time", classroom_name, True)
    result = courses.query(condition)[:limits]
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this classroom."
        )
    return result


@router.get("/searches/teacher/{teacher_name}", response_model=list[Course])
async def search_courses_by_teacher(
    teacher_name: str = Path(..., description="搜尋的教師姓名"),
    limits: int = Query(None, description="最大回傳資料筆數"),
):
    """
    根據教師姓名取得課程，可以用中英文姓名，也可以只用姓氏。
    """
    condition = Conditions("teacher", teacher_name, True)
    result = courses.query(condition)[:limits]
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this teacher."
        )
    return result


@router.get("/searches/credits/{credits_number}", response_model=list[Course])
async def search_courses_by_credits(
    credits_number: float = Path(..., description="搜尋的學分數"),
    op: Operation = Query(None, description="比較運算子，可以是 >(gt)、<(lt)、>=(gte)、<=(lte)"),
    limits: int = Query(None, description="最大回傳資料筆數"),
):
    """
    取得指定學分數的課程。
    """
    result = courses.list_credit(credits_number, op)[:limits]
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this credits."
        )
    return result
