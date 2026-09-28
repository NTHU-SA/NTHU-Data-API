"""Tests for courses endpoints."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app
from data_api.domain.courses.models import CourseData
from data_api.domain.courses.services import courses_service


@pytest.fixture(autouse=True)
def fixed_courses(monkeypatch):
    """These query tests supply their own snapshots; lifecycle tests use real refresh."""
    monkeypatch.setattr(courses_service, "course_data", [])
    monkeypatch.setattr(courses_service, "update_data", AsyncMock())


INVALID_REGEX_PATTERNS = [
    "[",
    "(",
    "\\",
    "*",
    "(?invalid)",
    pytest.param("a{99999999999999999999}", id="repeat-overflow"),
    pytest.param("(" * 1000, id="nesting-too-deep"),
]


class TestCoursesEndpoints:
    """Tests for courses endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    @pytest.mark.parametrize(
        "url",
        [
            "/courses/",
            "/courses/lists/microcredits",
            "/courses/lists/xclass",
        ],
    )
    async def test_courses_list_endpoints(self, client: AsyncClient, url: str):
        """Test courses list endpoints."""
        response = await client.get(url)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "field_name",
        [_.value for _ in schemas.courses.CourseFieldName],
    )
    async def test_courses_search_by_field(self, client: AsyncClient, field_name: str):
        """Test searching courses by field name."""
        response = await client.get(f"/courses/search?{field_name}=中")
        assert response.status_code == 200

    async def test_invalid_language_is_still_rejected(self, client: AsyncClient):
        response = await client.get("/courses/search", params={"language": "invalid"})
        assert response.status_code == 422

    @pytest.mark.parametrize("params", [{}, {"unknown": "ignored"}, {"teacher": ""}])
    async def test_absent_filters_return_empty_results(self, client: AsyncClient, params):
        response = await client.get("/courses/search", params=params)
        assert response.status_code == 200
        assert response.json() == []
        assert response.headers["X-Total-Count"] == "0"


def test_course_search_query_model_keeps_flat_optional_parameters():
    operation = app.openapi()["paths"]["/courses/search"]["get"]
    assert "requestBody" not in operation
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) == {field.value for field in schemas.courses.CourseFieldName}
    for parameter in parameters.values():
        assert parameter["in"] == "query"
        assert not parameter["required"]


class TestCoursesSearchPost:
    """Tests for courses POST search with conditions."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_search_with_single_condition(self, client: AsyncClient):
        """Test searching courses with single condition."""
        body = {
            "row_field": "chinese_title",
            "matcher": "數統導論",
            "regex_match": True,
        }
        response = await client.post("/courses/search", json=body)
        assert response.status_code == 200

    async def test_search_with_two_conditions(self, client: AsyncClient):
        """Test searching courses with two conditions using OR operator."""
        body = [
            {"row_field": "teacher", "matcher": "黃", "regex_match": True},
            "or",
            {"row_field": "teacher", "matcher": "孫", "regex_match": True},
        ]
        response = await client.post("/courses/search", json=body)
        assert response.status_code == 200

    async def test_search_with_multiple_conditions(self, client: AsyncClient):
        """Test searching courses with multiple nested conditions."""
        body = [
            {"row_field": "credit", "matcher": "3", "regex_match": True},
            "and",
            [
                [
                    {"row_field": "id", "matcher": "STAT", "regex_match": True},
                    "or",
                    {"row_field": "id", "matcher": "MATH", "regex_match": True},
                ],
                "and",
                [
                    {
                        "row_field": "class_room_and_time",
                        "matcher": "T3T4",
                        "regex_match": True,
                    },
                    "or",
                    {
                        "row_field": "class_room_and_time",
                        "matcher": "R3R4",
                        "regex_match": True,
                    },
                ],
            ],
        ]
        response = await client.post("/courses/search", json=body)
        assert response.status_code == 200

    async def test_search_with_flatten_conditions(self, client: AsyncClient):
        """Test searching courses with flatten multiple conditions."""
        body = [
            {"row_field": "chinese_title", "matcher": "微積分", "regex_match": True},
            "and",
            {"row_field": "credit", "matcher": "4", "regex_match": True},
            "and",
            {"row_field": "class_room_and_time", "matcher": "T", "regex_match": True},
        ]
        response = await client.post("/courses/search", json=body)
        assert response.status_code == 200


class TestCourseSearchValidation:
    """Exercise the exported app with deterministic, non-empty course data."""

    @pytest.fixture
    async def client(self, monkeypatch):
        monkeypatch.setattr(
            courses_service,
            "course_data",
            [
                CourseData.from_dict(
                    {
                        "id": "CS100",
                        "chinese_title": "程式設計",
                        "english_title": "C++ [AI]",
                        "teacher": "Teacher (AI)",
                        "language": "英",
                    }
                ),
                CourseData.from_dict(
                    {
                        "id": "MATH100",
                        "chinese_title": "微積分",
                        "english_title": "Calculus",
                        "teacher": "Someone else",
                        "language": "英",
                    }
                ),
            ],
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    @pytest.mark.parametrize("empty_data", [False, True])
    @pytest.mark.parametrize("pattern", INVALID_REGEX_PATTERNS)
    @pytest.mark.parametrize("field", ["chinese_title", "teacher", "id"])
    async def test_get_invalid_regex(self, client, monkeypatch, empty_data, pattern, field):
        if empty_data:
            monkeypatch.setattr(courses_service, "course_data", [])
        response = await client.get("/courses/search", params={field: pattern})
        assert response.status_code == 422
        assert response.json() == {
            "detail": f"Invalid regular expression for course field '{field}'."
        }

    @pytest.mark.parametrize("empty_data", [False, True])
    @pytest.mark.parametrize("nested", [False, True])
    @pytest.mark.parametrize("pattern", INVALID_REGEX_PATTERNS)
    async def test_post_invalid_regex(self, client, monkeypatch, empty_data, nested, pattern):
        if empty_data:
            monkeypatch.setattr(courses_service, "course_data", [])
        body = {"row_field": "teacher", "matcher": pattern, "regex_match": True}
        if nested:
            body = [
                {"row_field": "id", "matcher": "DOES_NOT_EXIST"},
                "and",
                [{"row_field": "credit", "matcher": "3"}, "or", body],
            ]
        response = await client.post("/courses/search", json=body)
        assert response.status_code == 422
        assert any(
            "Invalid regular expression" in error["msg"] for error in response.json()["detail"]
        )
        assert "Traceback" not in response.text

    async def test_get_preserves_regex_and_all_filters(self, client):
        response = await client.get(
            "/courses/search",
            params={"english_title": r"^C\+\+", "teacher": r"Teacher \(AI\)", "id": "^CS"},
        )
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == ["CS100"]
        assert response.headers["X-Total-Count"] == "1"

        response = await client.get(
            "/courses/search",
            params={"english_title": r"^C\+\+", "teacher": "impossible", "id": "^CS"},
        )
        assert response.status_code == 200
        assert response.json() == []
        assert response.headers["X-Total-Count"] == "0"

    @pytest.mark.parametrize("matcher", ["C++ [AI]", "C++", "["])
    async def test_post_preserves_exact_matching(self, client, matcher):
        response = await client.post(
            "/courses/search",
            json={"row_field": "english_title", "matcher": matcher, "regex_match": False},
        )
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == (
            ["CS100"] if matcher == "C++ [AI]" else []
        )

    async def test_post_preserves_nested_regex(self, client):
        response = await client.post(
            "/courses/search",
            json=[
                {"row_field": "id", "matcher": "^CS", "regex_match": True},
                "and",
                [
                    {"row_field": "teacher", "matcher": "absent"},
                    "or",
                    {"row_field": "english_title", "matcher": r"\[AI\]", "regex_match": True},
                ],
            ],
        )
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == ["CS100"]

    async def test_get_without_filters_remains_empty(self, client):
        response = await client.get("/courses/search")
        assert response.status_code == 200
        assert response.json() == []
