from enum import Enum
from fastapi import APIRouter, HTTPException, Query, Path
from ..models.courses import Conditions, Processor

router = APIRouter(
    prefix="/courses",
    tags=["courses"],
    responses={404: {"description": "Not found"}},
)

courses = Processor(json_path="data/courses/11210.json")


@router.get("/")
async def get_all_courses(limits: int = None):
    """
    取得所有課程。
    """
    try:
        result = courses.course_data[:limits]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/fields")
async def list_fields(limits: int = None):
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


@router.get("/fields/{field_name}")
async def list_selected_fields(field_name: str, limits: int = None):
    """
    取得指定欄位的列表。
    Args:
        field_name: 欄位名稱
    """
    try:
        result = courses.list_selected_fields(field_name)[:limits]
        return result
    except AttributeError as e:
        raise HTTPException(
            status_code=500, detail=f"The field '{field_name}' is not exist."
        )


@router.get("/fields/{field_name}/{value}")
async def search_by_field_and_value(field_name: str, value: str):
    """
    取得指定欄位的課程列表。
    Args:
        field_name: 搜尋的欄位名稱
        value: 搜尋的值
    """
    try:
        condition = Conditions(field_name, value, True)
        result = courses.query(condition)
        return result
    except KeyError as e:
        raise HTTPException(
            status_code=500, detail=f"The field '{field_name}' is not exist."
        )


class Language(str, Enum):
    Chinese = "中"
    English = "英"


@router.get("/languages/{language}")
async def search_courses_by_language(language: Language, limits: int = None):
    """
    取得指定語言的課程列表。
    Args:
        language: 搜尋的語言
    """
    condition = Conditions("language", language, True)
    result = courses.query(condition)[:limits]
    return result


@router.get("/credits/microcredits")
async def search_courses_by_credits(limits: int = None):
    """
    取得微學分課程列表。
    """
    condition = Conditions("credit", f"[0-9].[0-9]", True)
    result = courses.query(condition)[:limits]
    return result


@router.get("/durations/16weeks")
async def search_courses_by_duration(limits: int = None):
    """
    取得 16 週課程列表。
    """
    condition = Conditions("note", "本課程為16週課程", True)
    result = courses.query(condition)[:limits]
    return result


@router.get("/searches/id/{course_id}")
async def search_courses_by_id(course_id: str):
    """
    根據課號取得課程。
    Args:
        course_id: 搜尋的課號
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


@router.get("/searches/time/{class_time}")
async def search_courses_by_time(class_time: str):
    """
    根據上課時間取得課程，可以用 W1W2 表示星期一第一節到第二節。
    Args:
        class_time: 搜尋的上課時間
    """
    condition = Conditions("class_room_and_time", class_time, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(status_code=404, detail="There is no course at this time.")
    return result


@router.get("/searches/classroom/{classroom_name}")
async def search_courses_by_classroom(classroom_name: str):
    """
    根據教室取得課程，可以用中文或英文教室名稱，也可以使用系館代碼。
    Args:
        classroom: 搜尋的教室
    """
    condition = Conditions("class_room_and_time", classroom_name, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this classroom."
        )
    return result


@router.get("/searches/teacher/{teacher_name}")
async def search_courses_by_teacher(teacher_name: str, limits: int = None):
    """
    根據教師姓名取得課程，可以用中英文姓名，也可以只用姓氏
    Args:
        teacher_name: 搜尋的教師姓名
    """
    condition = Conditions("teacher", teacher_name, True)
    result = courses.query(condition)[:limits]
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this teacher."
        )
    return result


@router.get("/searches/credits/{credits_number}")
async def search_courses_by_credits(credits_number: str):
    """
    取得指定學分數的課程，可以用 2+ 或 2- 表示 2 學分以上或以下
    Args:
        credits_number: 搜尋的學分數
    """
    condition = Conditions("credit", f"[{credits_number}]", True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this credits."
        )
    return result
