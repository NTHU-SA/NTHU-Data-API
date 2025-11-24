"""
Courses domain models.

Pure Python domain models without FastAPI or Pydantic dependencies.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional, Union


@dataclass
class CourseData:
    """Course data model."""

    id: str
    chinese_title: str
    english_title: str
    credit: str
    size_limit: str
    freshman_reservation: str
    object: str
    ge_type: str
    language: str
    note: str
    suspend: str
    class_room_and_time: str
    teacher: str
    prerequisite: str
    limit_note: str
    expertise: str
    program: str
    no_extra_selection: str
    required_optional_note: str

    # Field mapping for converting from raw data
    FIELD_MAPPING = {
        "id": ["科號", "ID", "id"],
        "chinese_title": ["課程中文名稱", "CHINESE_TITLE", "chinese_title"],
        "english_title": ["課程英文名稱", "ENGLISH_TITLE", "english_title"],
        "credit": ["學分數", "CREDIT", "credit"],
        "size_limit": ["人限", "SIZE_LIMIT", "size_limit"],
        "freshman_reservation": [
            "新生保留人數",
            "FRESHMAN_RESERVATION",
            "freshman_reservation",
        ],
        "object": ["通識對象", "OBJECT", "object"],
        "ge_type": ["通識類別", "GE_TYPE", "ge_type"],
        "language": ["授課語言", "LANGUAGE", "language"],
        "note": ["備註", "NOTE", "note"],
        "suspend": ["停開註記", "SUSPEND", "suspend"],
        "class_room_and_time": [
            "教室與上課時間",
            "CLASS_ROOM_AND_TIME",
            "class_room_and_time",
        ],
        "teacher": ["授課教師", "TEACHER", "teacher"],
        "prerequisite": ["擋修說明", "PREREQUISITE", "prerequisite"],
        "limit_note": ["課程限制說明", "LIMIT_NOTE", "limit_note"],
        "expertise": ["第一二專長對應", "EXPERTISE", "expertise"],
        "program": ["學分學程對應", "PROGRAM", "program"],
        "no_extra_selection": [
            "不可加簽說明",
            "NO_EXTRA_SELECTION",
            "no_extra_selection",
        ],
        "required_optional_note": [
            "必選修說明",
            "REQUIRED_OPTIONAL_NOTE",
            "required_optional_note",
        ],
    }

    @classmethod
    def from_dict(cls, init_data: dict) -> "CourseData":
        """
        Create CourseData from dictionary using FIELD_MAPPING.
        Returns empty string for missing fields.
        """
        data = {}
        for canonical_field, keywords in cls.FIELD_MAPPING.items():
            found = False
            for key in keywords:
                if key in init_data:
                    data[canonical_field] = init_data[key]
                    found = True
                    break
            if not found:
                data[canonical_field] = ""
        return cls(**data)

    def __repr__(self) -> str:
        return str(self.__dict__)


@dataclass
class Condition:
    """Single condition for filtering courses."""

    row_field: str
    matcher: Union[str, re.Pattern]
    regex_match: bool = False

    def __post_init__(self):
        # Normalize field names to lowercase
        self.row_field = self.row_field.lower()

    def check(self, course: CourseData) -> bool:
        """Check if course satisfies this condition."""
        field_data = getattr(course, self.row_field, "")
        if self.regex_match:
            return re.search(self.matcher, field_data) is not None
        else:
            return field_data == self.matcher


ConditionType = Union[Condition, bool, dict, list]


@dataclass
class Conditions:
    """Complex condition tree for filtering courses."""

    condition_stat: Any = field(default=None)
    course: Optional[CourseData] = field(default=None, init=False)

    def __init__(
        self,
        row_field: Optional[str] = None,
        matcher: Optional[Union[str, re.Pattern]] = None,
        regex_match: bool = False,
        *,
        list_build_target: Optional[list[Any]] = None,
    ):
        if list_build_target is not None:
            self.condition_stat = list_build_target
        elif row_field is not None and matcher is not None:
            self.condition_stat = [
                Condition(row_field, matcher, regex_match),
                "and",
                True,
            ]
        else:
            raise ValueError("Must provide row_field and matcher, or list_build_target")
        self.course = None

    def __and__(self, other: "Conditions") -> "Conditions":
        return Conditions(
            list_build_target=[self.condition_stat, "and", other.condition_stat]
        )

    def __or__(self, other: "Conditions") -> "Conditions":
        return Conditions(
            list_build_target=[self.condition_stat, "or", other.condition_stat]
        )

    def _solve_condition_stat(self, data: Any) -> bool:
        """Recursively evaluate condition tree."""
        if not isinstance(data, list):
            return self._check_condition(data)

        if len(data) < 3:
            if not data:
                return True
            return self._check_condition(data[0])

        # Evaluate conditions iteratively
        result = self._check_condition(data[0])
        i = 1
        while i < len(data) - 1:
            op = data[i]
            next_condition = data[i + 1]
            next_condition_value = self._check_condition(next_condition)
            if op == "and":
                result = result and next_condition_value
            elif op == "or":
                result = result or next_condition_value
            else:
                raise ValueError(f"Unknown operator: {op}")
            i += 2
        return result

    def _check_condition(self, item: ConditionType) -> bool:
        """Check a single condition item."""
        if isinstance(item, dict):
            return Condition(**item).check(self.course)
        elif isinstance(item, list):
            return self._solve_condition_stat(item)
        elif isinstance(item, Condition):
            return item.check(self.course)
        elif isinstance(item, bool):
            return item
        else:
            raise TypeError(f"Cannot handle condition item: {item}")

    def accept(self, course: CourseData) -> bool:
        """Check if course satisfies all conditions."""
        self.course = course
        return self._solve_condition_stat(self.condition_stat)
