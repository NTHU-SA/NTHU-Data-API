"""Shared normalized course data and typed query models."""

import math
import re
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator

COURSE_QUERY_MAX_DEPTH = 32
COURSE_QUERY_MAX_NODES = 1024
SemesterCode = Annotated[str, Field(pattern=r"^[0-9]{5}$")]
NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]
Credits = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
CourseMatcher = str | int | float | bool | None


class CourseLanguage(StrEnum):
    Chinese = "zh"
    English = "en"


class LecturerLabel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    label: str | None


class LecturerNames(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    name_zh: str | None
    name_en: str | None


class CourseMeeting(BaseModel):
    model_config = ConfigDict(strict=True)
    classroom: str | None
    time: str | None
    time_codes: list[str] | None


class CourseExpertise(BaseModel):
    model_config = ConfigDict(strict=True)
    name: str | None
    type: str | None


class CurriculumRequirement(BaseModel):
    model_config = ConfigDict(strict=True)
    target: str | None
    requirement: str | None


class CourseData(BaseModel):
    """A published normalized course, including unknown values and parser warnings."""

    model_config = ConfigDict(strict=True)

    id: str = Field(min_length=1, description="課號")
    chinese_title: str
    english_title: str
    note: str
    limit_note: str
    object: str = Field(description="開課對象／選課限制")
    ge_type: str = Field(description="通識對象")
    ge_category: str = Field(description="通識分類")
    no_extra_selection: str
    semester_code: SemesterCode
    department_code: str | None
    course_number: str | None
    department_name: str | None
    college_name: str | None
    course_level_code: str | None
    course_level: str | None
    remote_teaching: str | None
    credits: Credits | None
    capacity: NonnegativeInt | None
    capacity_unlimited: bool | None
    enrolled_count: NonnegativeInt | None
    enrollment_after_selection: NonnegativeInt | None
    enrollment_after_withdrawal: NonnegativeInt | None
    reserved_for_freshmen: NonnegativeInt | None
    is_cancelled: bool | None
    language_code: str | None = Field(pattern=r"^(zh|en)$")
    lecturers: list[LecturerLabel | LecturerNames]
    meetings: list[CourseMeeting]
    expertises: list[CourseExpertise]
    programs: list[str]
    curriculum_requirements: list[CurriculumRequirement]
    prerequisite_text: str
    parsing_issues: list[str]

    @model_validator(mode="after")
    def check_identity(self) -> Self:
        if not self.id.startswith(self.semester_code) or not self.id[5:].strip():
            raise ValueError("Course ID must start with its semester and contain a course identity")
        if not (self.chinese_title.strip() or self.english_title.strip()):
            raise ValueError("A course must have a usable title")
        return self


class CourseCatalog(BaseModel):
    model_config = ConfigDict(strict=True)
    semesters: list[SemesterCode]

    @field_validator("semesters")
    @classmethod
    def unique_semesters(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate semesters")
        return sorted(value, reverse=True)


class CourseFieldName(StrEnum):
    id = "id"
    chinese_title = "chinese_title"
    english_title = "english_title"
    note = "note"
    limit_note = "limit_note"
    object = "object"
    ge_type = "ge_type"
    ge_category = "ge_category"
    no_extra_selection = "no_extra_selection"
    semester_code = "semester_code"
    department_code = "department_code"
    course_number = "course_number"
    department_name = "department_name"
    college_name = "college_name"
    course_level_code = "course_level_code"
    course_level = "course_level"
    remote_teaching = "remote_teaching"
    credits = "credits"
    capacity = "capacity"
    capacity_unlimited = "capacity_unlimited"
    enrolled_count = "enrolled_count"
    enrollment_after_selection = "enrollment_after_selection"
    enrollment_after_withdrawal = "enrollment_after_withdrawal"
    reserved_for_freshmen = "reserved_for_freshmen"
    is_cancelled = "is_cancelled"
    language_code = "language_code"
    lecturer_label = "lecturers.label"
    lecturer_name_zh = "lecturers.name_zh"
    lecturer_name_en = "lecturers.name_en"
    meeting_classroom = "meetings.classroom"
    meeting_time = "meetings.time"
    meeting_time_codes = "meetings.time_codes"
    expertise_name = "expertises.name"
    expertise_type = "expertises.type"
    programs = "programs"
    requirement_target = "curriculum_requirements.target"
    requirement = "curriculum_requirements.requirement"
    prerequisite_text = "prerequisite_text"
    parsing_issues = "parsing_issues"


INTEGER_FIELDS = {
    CourseFieldName.capacity.value,
    CourseFieldName.enrolled_count.value,
    CourseFieldName.enrollment_after_selection.value,
    CourseFieldName.enrollment_after_withdrawal.value,
    CourseFieldName.reserved_for_freshmen.value,
}
BOOLEAN_FIELDS = {
    CourseFieldName.capacity_unlimited.value,
    CourseFieldName.is_cancelled.value,
}
NUMERIC_OR_BOOLEAN_FIELDS = INTEGER_FIELDS | BOOLEAN_FIELDS | {CourseFieldName.credits.value}
NULLABLE_FIELDS = NUMERIC_OR_BOOLEAN_FIELDS | {
    CourseFieldName.department_code.value,
    CourseFieldName.course_number.value,
    CourseFieldName.department_name.value,
    CourseFieldName.college_name.value,
    CourseFieldName.course_level_code.value,
    CourseFieldName.course_level.value,
    CourseFieldName.remote_teaching.value,
    CourseFieldName.language_code.value,
    CourseFieldName.lecturer_label.value,
    CourseFieldName.lecturer_name_zh.value,
    CourseFieldName.lecturer_name_en.value,
    CourseFieldName.meeting_classroom.value,
    CourseFieldName.meeting_time.value,
    CourseFieldName.meeting_time_codes.value,
    CourseFieldName.expertise_name.value,
    CourseFieldName.expertise_type.value,
    CourseFieldName.requirement_target.value,
    CourseFieldName.requirement.value,
}


def _is_valid_credits_matcher(matcher: CourseMatcher) -> bool:
    if type(matcher) is int:
        return matcher >= 0
    if type(matcher) is float:
        return math.isfinite(matcher) and matcher >= 0
    return False


def _is_valid_matcher_value(field: str, matcher: CourseMatcher) -> bool:
    if matcher is None:
        return field in NULLABLE_FIELDS
    if field in BOOLEAN_FIELDS:
        return type(matcher) is bool
    if field in INTEGER_FIELDS:
        return type(matcher) is int and matcher >= 0
    if field == CourseFieldName.credits.value:
        return _is_valid_credits_matcher(matcher)
    return isinstance(matcher, str)


def validate_matcher(field: str, matcher: CourseMatcher, regex_match: bool) -> None:
    """Validate types before querying, including empty datasets."""
    CourseFieldName(field)
    if not _is_valid_matcher_value(field, matcher):
        raise ValueError(f"Invalid matcher type for course field '{field}'")
    if not regex_match:
        return
    if not isinstance(matcher, str) or field in NUMERIC_OR_BOOLEAN_FIELDS:
        raise ValueError("Regular expressions require a text field and string matcher")
    try:
        re.compile(matcher)
    except (re.error, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid regular expression") from exc


class CourseSearchParams(BaseModel):
    """AND filters: regex text, exact numbers/booleans, ANY over array leaves."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    chinese_title: str | None = None
    english_title: str | None = None
    note: str | None = None
    limit_note: str | None = None
    object: str | None = None
    ge_type: str | None = None
    ge_category: str | None = None
    no_extra_selection: str | None = None
    semester_code: str | None = None
    department_code: str | None = None
    course_number: str | None = None
    department_name: str | None = None
    college_name: str | None = None
    course_level_code: str | None = None
    course_level: str | None = None
    remote_teaching: str | None = None
    credits: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    capacity: Annotated[int, Field(ge=0)] | None = None
    capacity_unlimited: bool | None = None
    enrolled_count: Annotated[int, Field(ge=0)] | None = None
    enrollment_after_selection: Annotated[int, Field(ge=0)] | None = None
    enrollment_after_withdrawal: Annotated[int, Field(ge=0)] | None = None
    reserved_for_freshmen: Annotated[int, Field(ge=0)] | None = None
    is_cancelled: bool | None = None
    language_code: str | None = None
    lecturer_label: str | None = Field(None, alias=CourseFieldName.lecturer_label.value)
    lecturer_name_zh: str | None = Field(None, alias=CourseFieldName.lecturer_name_zh.value)
    lecturer_name_en: str | None = Field(None, alias=CourseFieldName.lecturer_name_en.value)
    meeting_classroom: str | None = Field(None, alias=CourseFieldName.meeting_classroom.value)
    meeting_time: str | None = Field(None, alias=CourseFieldName.meeting_time.value)
    meeting_time_codes: str | None = Field(None, alias=CourseFieldName.meeting_time_codes.value)
    expertise_name: str | None = Field(None, alias=CourseFieldName.expertise_name.value)
    expertise_type: str | None = Field(None, alias=CourseFieldName.expertise_type.value)
    programs: str | None = None
    requirement_target: str | None = Field(None, alias=CourseFieldName.requirement_target.value)
    requirement: str | None = Field(None, alias=CourseFieldName.requirement.value)
    prerequisite_text: str | None = None
    parsing_issues: str | None = None


class CourseCondition(BaseModel):
    model_config = ConfigDict(strict=True)
    row_field: CourseFieldName
    matcher: CourseMatcher
    regex_match: bool = False

    @field_validator("row_field", mode="before")
    @classmethod
    def parse_field(cls, value: Any) -> CourseFieldName:
        return CourseFieldName(value)

    @model_validator(mode="after")
    def check_matcher(self) -> Self:
        validate_matcher(self.row_field, self.matcher, self.regex_match)
        return self


class CourseQueryOperation(StrEnum):
    and_ = "and"
    or_ = "or"


class CourseQueryCondition(RootModel):
    """Alternate conditions and and/or, evaluated left to right; [] matches all.

    Maximum 32 array levels and 1024 nodes (arrays, condition objects and operators).
    """

    root: list["CourseQueryCondition | CourseCondition | CourseQueryOperation"]

    @field_validator("root", mode="before")
    @classmethod
    def check_query(cls, value: Any) -> Any:
        from data_api.domain.courses.models import validate_condition_sequence

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


class CourseListName(StrEnum):
    microcredits = "microcredits"
    xclass = "xclass"


class CourseGetParams(CourseSearchParams):
    type: CourseListName | None = None
