"""Regression coverage for the advanced course query grammar and tree budgets."""

from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from data_api.api.api import app
from data_api.api.schemas.courses import (
    COURSE_QUERY_MAX_DEPTH,
    COURSE_QUERY_MAX_NODES,
    CourseCondition,
    CourseQueryCondition,
)
from data_api.domain.courses.models import Conditions, CourseData
from data_api.domain.courses.services import courses_service

ALICE = {"row_field": "teacher", "matcher": "Alice"}
BOB = {"row_field": "teacher", "matcher": "Bob"}
THREE_CREDITS = {"row_field": "credit", "matcher": "3"}
FOUR_CREDITS = {"row_field": "credit", "matcher": "4"}

INVALID_QUERIES = [
    pytest.param([ALICE, BOB], id="adjacent-two"),
    pytest.param([ALICE, BOB, ALICE], id="adjacent-three"),
    pytest.param([ALICE, "and", BOB, ALICE], id="extra-trailing-condition"),
    pytest.param([ALICE, "and", "or", BOB], id="consecutive-operators"),
    pytest.param([ALICE, "and", "or", "and", BOB], id="operator-in-operand-position"),
    pytest.param(["and", ALICE], id="leading-operator"),
    pytest.param([ALICE, "or"], id="trailing-operator"),
    pytest.param(["and"], id="only-operator"),
    pytest.param([ALICE, "xor", BOB], id="unknown-operator"),
    pytest.param([ALICE, "AND", BOB], id="uppercase-operator"),
    pytest.param([ALICE, "and", [ALICE, BOB]], id="nested-adjacent"),
    pytest.param([[ALICE, BOB, ALICE]], id="wrapped-adjacent"),
    pytest.param([ALICE, "or", [BOB, "or"]], id="nested-trailing-operator"),
    pytest.param([ALICE, "and", True], id="boolean-operand"),
    pytest.param([42], id="numeric-operand"),
    pytest.param([None], id="null-operand"),
]

VALID_QUERIES = [
    pytest.param(ALICE, ["A"], id="single-object"),
    pytest.param([ALICE], ["A"], id="single-array"),
    pytest.param([], ["A", "B"], id="empty-array"),
    pytest.param([ALICE, "and", THREE_CREDITS], ["A"], id="and"),
    pytest.param([ALICE, "or", BOB], ["A", "B"], id="or"),
    pytest.param([[ALICE, "or", BOB], "and", THREE_CREDITS], ["A"], id="nested"),
    pytest.param([ALICE, "or", BOB, "and", FOUR_CREDITS], ["B"], id="left-to-right"),
    pytest.param([ALICE, "or", [BOB, "and", FOUR_CREDITS]], ["A", "B"], id="grouped"),
    pytest.param([[], "and", ALICE], ["A"], id="empty-and"),
    pytest.param([[], "or", ALICE], ["A", "B"], id="empty-or"),
    pytest.param([[]], ["A", "B"], id="nested-empty"),
    pytest.param(
        [{"row_field": "teacher", "matcher": "^A", "regex_match": True}, "or", BOB],
        ["A", "B"],
        id="regex",
    ),
]


def nested_query(depth):
    body = ALICE
    for _ in range(depth):
        body = [body]
    return body


def wide_query(conditions, operand=ALICE):
    body = [operand]
    for _ in range(conditions - 1):
        body.extend(["or", operand])
    return body


LIMIT_QUERIES = [
    pytest.param(nested_query(32), True, id="depth-at-limit"),
    pytest.param(nested_query(33), False, id="depth-over-limit"),
    pytest.param(nested_query(256), False, id="depth-beyond-recursive-parser-limit"),
    pytest.param(wide_query(512), True, id="1024-nodes"),
    pytest.param([wide_query(512)], False, id="1025-nodes"),
    pytest.param(wide_query(513), False, id="1026-nodes"),
    pytest.param(wide_query(512, []), True, id="1024-array-and-operator-nodes"),
    pytest.param([wide_query(512, [])], False, id="1025-array-and-operator-nodes"),
    pytest.param([wide_query(255), "and", wide_query(256)], True, id="1024-distributed-nodes"),
    pytest.param([wide_query(256), "and", wide_query(256)], False, id="1026-distributed-nodes"),
]


@pytest.fixture
def courses():
    return [
        CourseData.from_dict(
            {"id": course_id, "teacher": teacher, "credit": credit, "language": "英"}
        )
        for course_id, teacher, credit in [("A", "Alice", "3"), ("B", "Bob", "4")]
    ]


@pytest.mark.parametrize("body", INVALID_QUERIES)
def test_schema_rejects_invalid_grammar(body):
    with pytest.raises(ValidationError):
        CourseQueryCondition.model_validate(body)


@pytest.mark.parametrize("body,expected_ids", VALID_QUERIES)
def test_schema_preserves_legal_query_semantics(body, expected_ids, courses):
    schema = CourseCondition if isinstance(body, dict) else CourseQueryCondition
    parsed = schema.model_validate(body)
    conditions = Conditions(list_build_target=[parsed.model_dump(mode="json")])
    assert [course.id for course in courses if conditions.accept(course)] == expected_ids


@pytest.mark.parametrize("body,accepted", LIMIT_QUERIES)
def test_schema_enforces_exact_tree_limits(body, accepted):
    assert COURSE_QUERY_MAX_DEPTH == 32
    assert COURSE_QUERY_MAX_NODES == 1024
    if accepted:
        assert (
            CourseQueryCondition.model_validate(body).model_dump(mode="json", exclude_unset=True)
            == body
        )
    else:
        with pytest.raises(ValidationError, match="cannot exceed"):
            CourseQueryCondition.model_validate(body)


def test_limits_include_prevalidated_nested_models():
    wide = CourseQueryCondition.model_validate(wide_query(512))
    with pytest.raises(ValidationError, match="1024 nodes"):
        CourseQueryCondition.model_validate([wide])
    deep = CourseQueryCondition.model_validate(nested_query(32))
    with pytest.raises(ValidationError, match="32 array levels"):
        CourseQueryCondition.model_validate([deep])


def test_schema_accepts_prevalidated_conditions_and_nested_models():
    condition = CourseCondition.model_validate(ALICE)
    nested = CourseQueryCondition.model_validate([condition])
    parsed = CourseQueryCondition.model_validate([nested, "or", condition])
    assert parsed.model_dump(mode="json") == [
        [ALICE | {"regex_match": False}],
        "or",
        ALICE | {"regex_match": False},
    ]


@pytest.mark.parametrize("path", ["/courses/query", "/courses/search"])
@pytest.mark.parametrize("empty_data", [False, True])
class TestCourseQueryGrammarEndpoints:
    @pytest.fixture
    async def client(self, monkeypatch, courses, empty_data):
        monkeypatch.setattr(courses_service, "course_data", [] if empty_data else courses)
        monkeypatch.setattr(courses_service, "update_data", AsyncMock())
        monkeypatch.setattr(courses_service, "last_commit_hash", "grammar-test-version")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    @pytest.mark.parametrize("body", INVALID_QUERIES)
    async def test_invalid_grammar_returns_422(self, client, monkeypatch, path, empty_data, body):
        query = Mock(side_effect=AssertionError("Invalid queries must not be evaluated"))
        monkeypatch.setattr(courses_service, "query", query)
        response = await client.post(path, json=body)
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], list)
        assert "Traceback" not in response.text
        query.assert_not_called()

    @pytest.mark.parametrize("body,expected_ids", VALID_QUERIES)
    async def test_legal_queries_keep_results(self, client, path, empty_data, body, expected_ids):
        response = await client.post(path, json=body)
        assert response.status_code == 200
        expected_ids = [] if empty_data else expected_ids
        assert [course["id"] for course in response.json()] == expected_ids
        assert response.headers["X-Total-Count"] == str(len(expected_ids))
        assert response.headers["X-Data-Commit-Hash"] == "grammar-test-version"

    @pytest.mark.parametrize("body,accepted", LIMIT_QUERIES)
    async def test_tree_limits_return_422(self, client, path, empty_data, body, accepted):
        response = await client.post(path, json=body)
        assert response.status_code == (200 if accepted else 422)
        if accepted:
            expected_ids = (
                [] if empty_data else (["A", "B"] if body == wide_query(512, []) else ["A"])
            )
            assert [course["id"] for course in response.json()] == expected_ids
            assert response.headers["X-Total-Count"] == str(len(expected_ids))
        else:
            assert any("cannot exceed" in error["msg"] for error in response.json()["detail"])


@pytest.mark.parametrize("path", ["/courses/query", "/courses/search"])
def test_openapi_documents_grammar_validation(path):
    operation = app.openapi()["paths"][path]["post"]
    assert "grammar" in operation["responses"]["422"]["description"]
    schema = app.openapi()["components"]["schemas"]["CourseQueryCondition"]
    assert "32 array levels and 1024 nodes" in schema["description"]
