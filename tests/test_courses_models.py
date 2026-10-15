"""Normalized course structure, typed matchers and array query semantics."""

import pytest
from conftest import course_payload, make_course
from pydantic import ValidationError

from data_api.domain.courses.models import Condition, Conditions
from data_api.domain.courses.services import prepare_catalog, prepare_courses
from data_api.models.courses import CourseCondition, CourseData


def test_complete_normalized_course_and_union_shapes():
    payload = course_payload(
        lecturers=[{"label": "Historical teacher"}, {"name_zh": "姓名", "name_en": None}],
        meetings=[{"classroom": None, "time": "bad", "time_codes": None}],
        credits=None,
        language_code=None,
        is_cancelled=None,
        parsing_issues=["Unrecognized time code"],
    )
    assert CourseData.model_validate(payload).model_dump(mode="json") == payload
    assert len(payload) == 33


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": ""},
        {"id": "11410TEST100000"},
        {"semester_code": "１１５１０"},
        {"chinese_title": "", "english_title": " "},
        {"credits": True},
        {"credits": -1},
        {"credits": float("inf")},
        {"capacity": 1.5},
        {"capacity": True},
        {"enrolled_count": -1},
        {"is_cancelled": "false"},
        {"language_code": "中"},
        {"lecturers": [{"label": "A", "name_en": "B"}]},
        {"lecturers": [{"name_zh": "A"}]},
        {"meetings": [{"classroom": "R", "time": "M1"}]},
        {"programs": "Program"},
    ],
)
def test_invalid_candidates_rejected(overrides):
    with pytest.raises(ValidationError):
        prepare_courses([course_payload(**overrides)])


@pytest.mark.parametrize("field", list(course_payload()))
def test_missing_published_fields_are_not_silently_filled(field):
    payload = course_payload()
    del payload[field]
    with pytest.raises(ValidationError):
        prepare_courses([payload])


def test_snapshot_identity_and_semester_validation():
    from data_api.data.nthudata import FetchFailure

    with pytest.raises(FetchFailure, match="validation"):
        prepare_courses([course_payload(), course_payload()])
    with pytest.raises(FetchFailure, match="validation"):
        prepare_courses([course_payload()], "11420")
    with pytest.raises(FetchFailure, match="payload_type"):
        prepare_courses({})
    assert prepare_courses([]) == []
    assert prepare_catalog({"semesters": ["11420", "11510"], "ignored": True}) == ["11510", "11420"]
    for semesters in [["11510", "11510"], ["bad"], [11510]]:
        with pytest.raises(ValidationError):
            prepare_catalog({"semesters": semesters})


@pytest.mark.parametrize(
    "field,matcher,regex",
    [
        ("credits", "3", False),
        ("credits", True, False),
        ("credits", float("nan"), False),
        ("capacity", 3.5, False),
        ("capacity", -1, False),
        ("is_cancelled", 0, False),
        ("chinese_title", 3, False),
        ("id", None, False),
        ("credits", 3, True),
        ("credits", "3", True),
        ("note", None, True),
        ("unknown", "x", False),
        ("teacher", "x", False),
    ],
)
def test_matcher_type_validation(field, matcher, regex):
    with pytest.raises(ValidationError):
        CourseCondition(row_field=field, matcher=matcher, regex_match=regex)


def test_array_leaves_and_null_do_not_match_absent_keys_or_empty_arrays():
    course = make_course(
        lecturers=[{"label": "Alice"}, {"name_zh": "Bob", "name_en": None}],
        meetings=[{"classroom": None, "time": "bad", "time_codes": None}],
        programs=["Program A", "Program B"],
    )
    assert Condition("lecturers.label", "Alice").check(course)
    assert Condition("lecturers.name_en", None).check(course)
    assert Condition("meetings.time_codes", None).check(course)
    assert Condition("programs", "B", True).check(course)
    assert not Condition("lecturers.label", None).check(course)
    assert not Condition("programs", "").check(course)
    empty = make_course()
    assert not Condition("lecturers.name_en", None).check(empty)
    assert not Condition("meetings.time_codes", None).check(empty)
    assert not Condition("programs", "A").check(empty)
    assert Condition("is_cancelled", False).check(empty)
    assert Condition("reserved_for_freshmen", 0).check(empty)


def test_independent_any_conditions_and_cached_predicate():
    course = make_course(lecturers=[{"label": "Alice"}, {"name_zh": "Bob", "name_en": None}])
    conditions = Conditions("lecturers.label", "Alice") & Conditions("lecturers.name_zh", "Bob")
    assert conditions.accept(course)
    predicate = conditions._predicate
    assert conditions.accept(course)
    assert conditions._predicate is predicate
    assert not hasattr(conditions, "course")
    assert (Conditions("id", "absent") | conditions).accept(course)


@pytest.mark.parametrize("body", [["and"], [True, "xor", True], [True, True], [42], [None]])
def test_domain_invalid_conditions(body):
    with pytest.raises((ValueError, TypeError)):
        Conditions(list_build_target=body).accept(make_course())


def test_conditions_require_a_field_or_sequence():
    with pytest.raises(ValueError):
        Conditions()
