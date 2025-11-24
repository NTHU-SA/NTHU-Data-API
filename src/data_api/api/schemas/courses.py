"""Courses API schemas."""

from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, RootModel, field_validator


class CourseFieldName(str, Enum):
    """Course field names for querying."""
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


class CourseLanguage(str, Enum):
    """Course language options."""
    Chinese = "中"
    English = "英"


class CourseCreditOperation(str, Enum):
    """Credit comparison operations."""
    GreaterThan = "gt"
    LessThan = "lt"
    GreaterThanOrEqual = "gte"
    LessThanOrEqual = "lte"


class CourseData(BaseModel):
    """Course data schema."""
    id: str = Field(..., description="課號")
    chinese_title: str = Field(..., description="課程中文名稱")
    english_title: str = Field(..., description="課程英文名稱")
    credit: str = Field(..., description="學分數")
    size_limit: str = Field(..., description="人限")
    freshman_reservation: str = Field(..., description="新生保留人數")
    object: str = Field(..., description="通識對象")
    ge_type: str = Field(..., description="通識類別")
    language: CourseLanguage = Field(..., description="授課語言")
    note: str = Field(..., description="備註")
    suspend: str = Field(..., description="停開註記")
    class_room_and_time: str = Field(..., description="教室與上課時間")
    teacher: str = Field(..., description="授課教師")
    prerequisite: str = Field(..., description="擋修說明")
    limit_note: str = Field(..., description="課程限制說明")
    expertise: str = Field(..., description="第一二專長對應")
    program: str = Field(..., description="學分學程對應")
    no_extra_selection: str = Field(..., description="不可加簽說明")
    required_optional_note: str = Field(..., description="必選修說明")


class CourseCondition(BaseModel):
    """Single course query condition."""
    row_field: CourseFieldName = Field(..., description="搜尋的欄位名稱")
    matcher: str = Field(..., description="搜尋的值")
    regex_match: bool = Field(False, description="是否使用正則表達式")


class CourseQueryOperation(str, Enum):
    """Query operation type."""
    and_ = "and"
    or_ = "or"


class CourseQueryCondition(RootModel):
    """Complex course query condition."""
    root: list[Union[Union["CourseQueryCondition", CourseCondition], CourseQueryOperation]]

    @field_validator("root")
    def check_query(cls, v):
        POST_ERROR_INFO = " Structure: [(nested) Condition, Operation, (nested) Condition]."
        for i in range(len(v)):
            if type(v[i]) is CourseQueryOperation:
                if i == 0 or i == len(v) - 1:
                    raise ValueError("First/last elements must be Condition." + POST_ERROR_INFO)
                elif type(v[i - 1]) not in [CourseQueryCondition, CourseCondition]:
                    raise TypeError("Before Operation must be Condition." + POST_ERROR_INFO)
                elif type(v[i + 1]) not in [CourseQueryCondition, CourseCondition]:
                    raise TypeError("After Operation must be Condition." + POST_ERROR_INFO)
        return v


class CourseListName(str, Enum):
    """Predefined course lists."""
    microcredits = "microcredits"
    xclass = "xclass"
