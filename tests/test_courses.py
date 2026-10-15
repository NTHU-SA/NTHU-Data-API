"""Course REST query regression tests using normalized offline snapshots."""

import pytest
from conftest import make_course, set_courses
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.models.courses import BOOLEAN_FIELDS, INTEGER_FIELDS, CourseFieldName

INVALID_REGEX_PATTERNS = ["[", "(", "\\", "*", "(?invalid)", "a{99999999999999999999}", "(" * 1000]


@pytest.fixture
def courses():
    return [
        make_course(
            id=f"11510{identity}",
            chinese_title=title,
            english_title=english,
            lecturers=[{"label": teacher}],
            credits=credits,
            note=note,
        )
        for identity, teacher, title, english, credits, note in [
            ("A", "林福仁", "服務學習", "C++ [AI]", 0.5, "X-Class"),
            ("B", "林福仁", "程式設計", "Programming", 3, ""),
            ("C", "黃老師", "服務設計", "Design", 1.5, ""),
            ("D", "孫老師", "跨域學習", "Learning", 2, "X-Class"),
        ]
    ]


@pytest.fixture
async def client(monkeypatch, courses):
    set_courses(monkeypatch, courses)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def test_course_search_query_model_keeps_flat_optional_parameters():
    operation = app.openapi()["paths"]["/courses"]["get"]
    assert "requestBody" not in operation
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) == {field.value for field in CourseFieldName} | {"type"}
    assert all(p["in"] == "query" and not p["required"] for p in parameters.values())


@pytest.mark.parametrize("field", [field.value for field in CourseFieldName])
async def test_every_get_field_is_accepted(client, field):
    value = (
        "false"
        if field in BOOLEAN_FIELDS
        else (
            "0"
            if field in INTEGER_FIELDS | {"credits"}
            else ("zh" if field == "language_code" else "中")
        )
    )
    assert (await client.get("/courses", params={field: value})).status_code == 200


@pytest.mark.parametrize(
    "params,ids",
    [
        ({}, ["A", "B", "C", "D"]),
        ({"lecturers.label": ""}, ["A", "B", "C", "D"]),
        ({"lecturers.label": "林福仁"}, ["A", "B"]),
        ({"chinese_title": "服務"}, ["A", "C"]),
        ({"lecturers.label": "林福仁", "chinese_title": "服務"}, ["A"]),
        ({"type": "microcredits"}, ["A", "C"]),
        ({"type": "xclass"}, ["A", "D"]),
        ({"type": "xclass", "lecturers.label": "林福仁"}, ["A"]),
        ({"type": "microcredits", "lecturers.label": "林福仁"}, ["A"]),
        ({"type": "xclass", "lecturers.label": "黃"}, []),
        ({"english_title": r"^C\+\+", "id": "^11510A"}, ["A"]),
        ({"credits": "3", "is_cancelled": "false", "reserved_for_freshmen": "0"}, ["B"]),
        ({"is_cancelled": "true"}, []),
    ],
)
async def test_get_collection_filters(client, params, ids):
    response = await client.get("/courses", params=params)
    assert response.status_code == 200, response.text
    assert [course["id"] for course in response.json()] == [f"11510{i}" for i in ids]
    assert response.headers["X-Total-Count"] == str(len(ids))
    assert response.headers["X-Data-Commit-Hash"] == "course-test-version"
    assert not response.history


@pytest.mark.parametrize(
    "params",
    [
        {"type": "unknown"},
        {"type": ""},
        {"type": "XCLASS"},
        {"language_code": "中"},
        {"credits": "bad"},
        {"capacity": "1.5"},
        {"is_cancelled": "bad"},
        {"teacher": "old"},
        {"credit": "3"},
    ],
)
async def test_invalid_get_filters(client, params):
    assert (await client.get("/courses", params=params)).status_code == 422


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("pattern", INVALID_REGEX_PATTERNS)
@pytest.mark.parametrize("field", ["chinese_title", "lecturers.label", "id"])
async def test_get_invalid_regex(client, monkeypatch, empty, pattern, field):
    if empty:
        set_courses(monkeypatch, [])
    response = await client.get("/courses", params={field: pattern})
    assert response.status_code == 422
    assert response.json() == {"detail": f"Invalid regular expression for course field '{field}'."}


@pytest.mark.parametrize("matcher", ["C++ [AI]", "C++", "["])
async def test_post_exact_text(client, matcher):
    response = await client.post(
        "/courses/query", json={"row_field": "english_title", "matcher": matcher}
    )
    assert response.status_code == 200
    assert [course["id"] for course in response.json()] == (
        ["11510A"] if matcher == "C++ [AI]" else []
    )


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("pattern", INVALID_REGEX_PATTERNS)
async def test_post_invalid_regex(client, monkeypatch, empty, nested, pattern):
    if empty:
        set_courses(monkeypatch, [])
    body = {"row_field": "lecturers.label", "matcher": pattern, "regex_match": True}
    if nested:
        body = [{"row_field": "id", "matcher": "absent"}, "and", [body]]
    response = await client.post("/courses/query", json=body)
    assert response.status_code == 422
    assert any("Invalid regular expression" in e["msg"] for e in response.json()["detail"])


async def test_post_nested_regex_and_typed_matchers(client):
    response = await client.post(
        "/courses/query",
        json=[
            {"row_field": "is_cancelled", "matcher": False},
            "and",
            [
                {"row_field": "credits", "matcher": 0.5},
                "or",
                {"row_field": "lecturers.label", "matcher": "黃", "regex_match": True},
            ],
        ],
    )
    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == ["11510A", "11510C"]
    assert response.headers["X-Total-Count"] == "2"
    assert response.headers["X-Data-Commit-Hash"] == "course-test-version"


async def test_large_integer_credit_matcher_does_not_overflow(client):
    response = await client.post(
        "/courses/query", json={"row_field": "credits", "matcher": 10**400}
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_response_is_full_normalized_shape_and_nullable(client, monkeypatch):
    course = make_course(credits=None, capacity_unlimited=None, language_code=None)
    set_courses(monkeypatch, [course], version=None)
    response = await client.get("/courses")
    assert response.json() == [course.model_dump(mode="json")]
    assert "X-Data-Commit-Hash" not in response.headers
    assert (
        await client.post("/courses/query", json={"row_field": "credits", "matcher": None})
    ).json() == response.json()
    assert (await client.get("/courses?type=microcredits")).json() == []
