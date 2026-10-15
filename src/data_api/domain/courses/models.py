"""
Courses domain models.

Pure Python domain models without FastAPI or Pydantic dependencies.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
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
    _pattern: re.Pattern | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        # Normalize field names to lowercase
        self.row_field = self.row_field.lower()
        if self.regex_match:
            self._pattern = re.compile(self.matcher)

    def check(self, course: CourseData) -> bool:
        """Check if course satisfies this condition."""
        field_data = getattr(course, self.row_field, "")
        if self._pattern is not None:
            return self._pattern.search(field_data) is not None
        else:
            return field_data == self.matcher


ConditionType = Union[Condition, bool, dict, list]


def validate_condition_sequence(
    sequence: list[Any],
    *,
    operand_types: tuple[type, ...] = (Condition, bool, dict, list),
) -> None:
    """Validate alternating operands and operators without evaluating conditions."""
    if sequence and len(sequence) % 2 == 0:
        raise ValueError("Condition arrays must have an odd number of elements.")
    for index, item in enumerate(sequence):
        if index % 2 == 0:
            if not isinstance(item, operand_types):
                raise ValueError("Expected a condition object or nested array at even positions.")
        elif not isinstance(item, str) or item not in ("and", "or"):
            raise ValueError("Unknown operator; expected 'and' or 'or' at odd positions.")


@dataclass
class Conditions:
    """Complex condition tree for filtering courses."""

    condition_stat: Any = field(default=None)

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

    def __and__(self, other: "Conditions") -> "Conditions":
        return Conditions(list_build_target=[self.condition_stat, "and", other.condition_stat])

    def __or__(self, other: "Conditions") -> "Conditions":
        return Conditions(list_build_target=[self.condition_stat, "or", other.condition_stat])

    @staticmethod
    def _prepare(item: ConditionType) -> Callable[[CourseData], bool]:
        if isinstance(item, dict):
            return Condition(**item).check
        elif isinstance(item, list):
            validate_condition_sequence(item)
            if not item:
                return lambda course: True
            operands = [Conditions._prepare(value) for value in item[::2]]
            operators = tuple(item[1::2])

            def evaluate(course: CourseData) -> bool:
                result = operands[0](course)
                for operator, predicate in zip(operators, operands[1:], strict=True):
                    value = predicate(course)
                    result = result and value if operator == "and" else result or value
                return result

            return evaluate
        elif isinstance(item, Condition):
            return item.check
        elif isinstance(item, bool):
            return lambda course: item
        else:
            raise TypeError(f"Cannot handle condition item: {item}")

    @cached_property
    def _predicate(self) -> Callable[[CourseData], bool]:
        return self._prepare(self.condition_stat)

    def accept(self, course: CourseData) -> bool:
        """Check if course satisfies all conditions."""
        return self._predicate(course)
