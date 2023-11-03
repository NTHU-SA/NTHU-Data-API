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
    try:
        result = courses.course_data[:limits]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/fields")
async def list_fields(limits: int = None):
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


@router.get("/fields/{field}")
async def list_selected_fields(field: str, limits: int = None):
    try:
        result = courses.list_selected_fields(field)[:limits]
        return result
    except AttributeError as e:
        raise HTTPException(
            status_code=500, detail=f"The field '{field}' is not exist."
        )


@router.get("/fields/{field}/{value}")
async def search_by_field_and_value(field: str, value: str):
    try:
        condition = Conditions(field, value, True)
        result = courses.query(condition)
        return result
    except KeyError as e:
        raise HTTPException(
            status_code=500, detail=f"The field '{field}' is not exist."
        )


class Language(str, Enum):
    Chinese = "中"
    English = "英"


@router.get("/languages/{language}")
async def search_courses_by_language(language: Language):
    condition = Conditions("language", language, True)
    result = courses.query(condition)
    return result


@router.get("/credits/microcredits")
async def search_courses_by_credits():
    condition = Conditions("credit", f"[0-9].[0-9]", True)
    result = courses.query(condition)
    return result


@router.get("/durations/16weeks")
async def search_courses_by_duration():
    condition = Conditions("note", "本課程為16週課程", True)
    result = courses.query(condition)
    return result


@router.get("/searches/id/{course_id}")
async def search_courses_by_id(course_id: str):
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


@router.get("/searches/time/{time}")
async def search_courses_by_time(time: str):
    condition = Conditions("class_room_and_time", time, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(status_code=404, detail="There is no course at this time.")
    return result


@router.get("/searches/classroom/{classroom}")
async def search_courses_by_classroom(classroom: str):
    condition = Conditions("class_room_and_time", classroom, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this classroom."
        )
    return result


@router.get("/searches/teacher/{teacher}")
async def search_courses_by_teacher(teacher: str):
    condition = Conditions("teacher", teacher, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this teacher."
        )
    return result


@router.get("/searches/credits/{credits}")
async def search_courses_by_credits(credits: str):
    """
    可以用 2+ 或 2- 表示 2 學分以上或以下
    """
    condition = Conditions("credit", credits, True)
    result = courses.query(condition)
    if result == []:
        raise HTTPException(
            status_code=404, detail="There is no course at this credits."
        )
    return result
