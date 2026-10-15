"""
Courses domain models.

Typed course predicates, independent of HTTP transports.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Optional, Union

from pydantic import BaseModel

from data_api.models.courses import CourseData, CourseMatcher, validate_matcher


def field_values(value: Any, path: list[str]) -> list[CourseMatcher]:
    """Resolve array leaves without confusing absent union keys with explicit null."""
    if isinstance(value, list):
        return [leaf for item in value for leaf in field_values(item, path)]
    if not path:
        return [value]
    key, *rest = path
    if isinstance(value, BaseModel):
        if key not in type(value).model_fields:
            return []
        return field_values(getattr(value, key), rest)
    return []


@dataclass
class Condition:
    """Single condition for filtering courses."""

    row_field: str
    matcher: CourseMatcher
    regex_match: bool = False
    _pattern: re.Pattern | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        validate_matcher(self.row_field, self.matcher, self.regex_match)
        if self.regex_match and isinstance(self.matcher, str):
            self._pattern = re.compile(self.matcher)

    def check(self, course: CourseData) -> bool:
        """Check if course satisfies this condition."""
        for value in field_values(course, self.row_field.split(".")):
            if self._pattern is not None:
                if isinstance(value, str) and self._pattern.search(value) is not None:
                    return True
            elif value == self.matcher:
                return True
        return False


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
        matcher: CourseMatcher = None,
        regex_match: bool = False,
        *,
        list_build_target: Optional[list[Any]] = None,
    ):
        if list_build_target is not None:
            self.condition_stat = list_build_target
        elif row_field is not None:
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
