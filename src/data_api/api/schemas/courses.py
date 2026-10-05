"""Courses API schemas."""

import re
from enum import Enum
from typing import Any, Self, Union

from pydantic import BaseModel, Field, RootModel, field_validator, model_validator

from data_api.domain.courses.models import validate_condition_sequence

COURSE_QUERY_MAX_DEPTH = 32
COURSE_QUERY_MAX_NODES = 1024


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


class CourseSearchParams(BaseModel):
    """Optional GET filters, combined with AND using regular-expression matching."""

    id: str | None = Field(None, description="課號")
    chinese_title: str | None = Field(None, description="課程中文名稱")
    english_title: str | None = Field(None, description="課程英文名稱")
    credit: str | None = Field(None, description="學分數")
    size_limit: str | None = Field(None, description="人限")
    freshman_reservation: str | None = Field(None, description="新生保留人數")
    object: str | None = Field(None, description="通識對象")
    ge_type: str | None = Field(None, description="通識類別")
    language: CourseLanguage | None = Field(None, description="授課語言")
    note: str | None = Field(None, description="備註")
    suspend: str | None = Field(None, description="停開註記")
    class_room_and_time: str | None = Field(None, description="教室與上課時間")
    teacher: str | None = Field(None, description="授課教師")
    prerequisite: str | None = Field(None, description="擋修說明")
    limit_note: str | None = Field(None, description="課程限制說明")
    expertise: str | None = Field(None, description="第一二專長對應")
    program: str | None = Field(None, description="學分學程對應")
    no_extra_selection: str | None = Field(None, description="不可加簽說明")
    required_optional_note: str | None = Field(None, description="必選修說明")


class CourseCondition(BaseModel):
    """Single course query condition."""

    row_field: CourseFieldName = Field(..., description="搜尋的欄位名稱")
    matcher: str = Field(..., description="搜尋的值")
    regex_match: bool = Field(False, description="是否使用正則表達式")

    @model_validator(mode="after")
    def check_regex(self) -> Self:
        """Validate regex syntax even when no course data is available."""
        if self.regex_match:
            try:
                re.compile(self.matcher)
            except (re.error, OverflowError, RecursionError) as exc:
                raise ValueError("Invalid regular expression") from exc
        return self


class CourseQueryOperation(str, Enum):
    """Query operation type."""

    and_ = "and"
    or_ = "or"


class CourseQueryCondition(RootModel):
    """Complex course query condition.

    Alternate conditions and 'and'/'or', evaluated left to right; empty arrays match all courses.
    Maximum 32 array levels and 1024 nodes (arrays, condition objects and operators).
    """

    root: list[Union[Union["CourseQueryCondition", CourseCondition], CourseQueryOperation]]

    @field_validator("root", mode="before")
    @classmethod
    def check_query(cls, value: Any) -> Any:
        """Bound and validate the whole tree before recursive model validation."""
        if not isinstance(value, list):
            return value
        pending = [(value, 1)]
        nodes = 0
        while pending:
            item, depth = pending.pop()
            nodes += 1
            if isinstance(item, CourseQueryCondition):
                item = item.root
            if not isinstance(item, list):
                continue
            if depth > COURSE_QUERY_MAX_DEPTH:
                raise ValueError(
                    f"Course queries cannot exceed {COURSE_QUERY_MAX_DEPTH} array levels."
                )
            if nodes + len(pending) + len(item) > COURSE_QUERY_MAX_NODES:
                raise ValueError(f"Course queries cannot exceed {COURSE_QUERY_MAX_NODES} nodes.")
            validate_condition_sequence(
                item, operand_types=(list, dict, CourseCondition, CourseQueryCondition)
            )
            pending.extend((child, depth + 1) for child in item)
        return value


class CourseListName(str, Enum):
    """Predefined course lists."""

    microcredits = "microcredits"
    xclass = "xclass"


class CourseGetParams(CourseSearchParams):
    """Course collection filters, including a predefined course type."""

    type: CourseListName | None = Field(None, description="課程類型")
