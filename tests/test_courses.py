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
    monkeypatch.setattr(courses_service, "last_commit_hash", "course-test-version")


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
            "/courses",
            "/courses/",
            "/courses?type=microcredits",
            "/courses?type=xclass",
            "/courses/lists/microcredits",
            "/courses/lists/xclass",
        ],
    )
    async def test_courses_list_endpoints(self, client: AsyncClient, url: str):
        """Test courses list endpoints."""
        response = await client.get(url)
        assert response.status_code == 200

    @pytest.mark.parametrize("path", ["/courses", "/courses/search"])
    @pytest.mark.parametrize(
        "field_name",
        [_.value for _ in schemas.courses.CourseFieldName],
    )
    async def test_courses_search_by_field(self, client: AsyncClient, field_name: str, path):
        """Test searching courses by field name."""
        response = await client.get(path, params={field_name: "中"})
        assert response.status_code == 200

    @pytest.mark.parametrize("path", ["/courses", "/courses/search"])
    async def test_invalid_language_is_still_rejected(self, client: AsyncClient, path):
        response = await client.get(path, params={"language": "invalid"})
        assert response.status_code == 422

    @pytest.mark.parametrize("params", [{}, {"unknown": "ignored"}, {"teacher": ""}])
    async def test_absent_filters_return_empty_results(self, client: AsyncClient, params):
        response = await client.get("/courses/search", params=params)
        assert response.status_code == 200
        assert response.json() == []
        assert response.headers["X-Total-Count"] == "0"


@pytest.mark.parametrize("path", ["/courses", "/courses/search"])
def test_course_search_query_model_keeps_flat_optional_parameters(path):
    operation = app.openapi()["paths"][path]["get"]
    assert "requestBody" not in operation
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    expected = {field.value for field in schemas.courses.CourseFieldName}
    if path == "/courses":
        expected.add("type")
    assert set(parameters) == expected
    for parameter in parameters.values():
        assert parameter["in"] == "query"
        assert not parameter["required"]


@pytest.mark.parametrize("post_path", ["/courses/query", "/courses/search"])
class TestCoursesSearchPost:
    """Tests for courses POST search with conditions."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_search_with_single_condition(self, client: AsyncClient, post_path):
        """Test searching courses with single condition."""
        body = {
            "row_field": "chinese_title",
            "matcher": "數統導論",
            "regex_match": True,
        }
        response = await client.post(post_path, json=body)
        assert response.status_code == 200

    async def test_search_with_two_conditions(self, client: AsyncClient, post_path):
        """Test searching courses with two conditions using OR operator."""
        body = [
            {"row_field": "teacher", "matcher": "黃", "regex_match": True},
            "or",
            {"row_field": "teacher", "matcher": "孫", "regex_match": True},
        ]
        response = await client.post(post_path, json=body)
        assert response.status_code == 200

    async def test_search_with_multiple_conditions(self, client: AsyncClient, post_path):
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
        response = await client.post(post_path, json=body)
        assert response.status_code == 200

    async def test_search_with_flatten_conditions(self, client: AsyncClient, post_path):
        """Test searching courses with flatten multiple conditions."""
        body = [
            {"row_field": "chinese_title", "matcher": "微積分", "regex_match": True},
            "and",
            {"row_field": "credit", "matcher": "4", "regex_match": True},
            "and",
            {"row_field": "class_room_and_time", "matcher": "T", "regex_match": True},
        ]
        response = await client.post(post_path, json=body)
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
    @pytest.mark.parametrize("path", ["/courses", "/courses/search"])
    @pytest.mark.parametrize("pattern", INVALID_REGEX_PATTERNS)
    @pytest.mark.parametrize("field", ["chinese_title", "teacher", "id"])
    async def test_get_invalid_regex(self, client, monkeypatch, empty_data, pattern, field, path):
        if empty_data:
            monkeypatch.setattr(courses_service, "course_data", [])
        response = await client.get(path, params={field: pattern})
        assert response.status_code == 422
        assert response.json() == {
            "detail": f"Invalid regular expression for course field '{field}'."
        }

    @pytest.mark.parametrize("empty_data", [False, True])
    @pytest.mark.parametrize("path", ["/courses/query", "/courses/search"])
    @pytest.mark.parametrize("nested", [False, True])
    @pytest.mark.parametrize("pattern", INVALID_REGEX_PATTERNS)
    async def test_post_invalid_regex(self, client, monkeypatch, empty_data, nested, pattern, path):
        if empty_data:
            monkeypatch.setattr(courses_service, "course_data", [])
        body = {"row_field": "teacher", "matcher": pattern, "regex_match": True}
        if nested:
            body = [
                {"row_field": "id", "matcher": "DOES_NOT_EXIST"},
                "and",
                [{"row_field": "credit", "matcher": "3"}, "or", body],
            ]
        response = await client.post(path, json=body)
        assert response.status_code == 422
        assert any(
            "Invalid regular expression" in error["msg"] for error in response.json()["detail"]
        )
        assert "Traceback" not in response.text

    @pytest.mark.parametrize("path", ["/courses", "/courses/search"])
    async def test_get_preserves_regex_and_all_filters(self, client, path):
        response = await client.get(
            path,
            params={"english_title": r"^C\+\+", "teacher": r"Teacher \(AI\)", "id": "^CS"},
        )
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == ["CS100"]
        assert response.headers["X-Total-Count"] == "1"

        response = await client.get(
            path,
            params={"english_title": r"^C\+\+", "teacher": "impossible", "id": "^CS"},
        )
        assert response.status_code == 200
        assert response.json() == []
        assert response.headers["X-Total-Count"] == "0"

    @pytest.mark.parametrize("matcher", ["C++ [AI]", "C++", "["])
    @pytest.mark.parametrize("path", ["/courses/query", "/courses/search"])
    async def test_post_preserves_exact_matching(self, client, matcher, path):
        response = await client.post(
            path,
            json={"row_field": "english_title", "matcher": matcher, "regex_match": False},
        )
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == (
            ["CS100"] if matcher == "C++ [AI]" else []
        )

    @pytest.mark.parametrize("path", ["/courses/query", "/courses/search"])
    async def test_post_preserves_nested_regex(self, client, path):
        response = await client.post(
            path,
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
        assert response.headers["X-Total-Count"] == "1"
        assert response.headers["X-Data-Commit-Hash"] == "course-test-version"

    async def test_get_without_filters_remains_empty(self, client):
        response = await client.get("/courses/search")
        assert response.status_code == 200
        assert response.json() == []


def test_course_endpoint_deprecations_and_operation_ids():
    paths = app.openapi()["paths"]
    operations = [
        ("/courses", "get", "getCourses", False),
        ("/courses/query", "post", "queryCourses", False),
        ("/courses/", "get", "getAllCourses", True),
        ("/courses/search", "get", "searchCoursesByFieldAndValue", True),
        ("/courses/search", "post", "searchCoursesByCondition", True),
        ("/courses/lists/{list_name}", "get", "listCoursesByType", True),
    ]
    for path, method, operation_id, deprecated in operations:
        operation = paths[path][method]
        assert operation["operationId"] == operation_id
        assert operation.get("deprecated", False) is deprecated
        if deprecated:
            assert "已棄用" in operation["description"]
    assert len({operation_id for _, _, operation_id, _ in operations}) == len(operations)
    assert (
        paths["/courses/query"]["post"]["requestBody"]
        == paths["/courses/search"]["post"]["requestBody"]
    )


class TestCourseCollection:
    @pytest.fixture
    async def client(self, monkeypatch):
        monkeypatch.setattr(
            courses_service,
            "course_data",
            [
                CourseData.from_dict(
                    {
                        "id": course_id,
                        "teacher": teacher,
                        "chinese_title": title,
                        "credit": credit,
                        "note": note,
                        "language": "中",
                    }
                )
                for course_id, teacher, title, credit, note in [
                    ("A", "林福仁", "服務學習", "0.5", "X-Class"),
                    ("B", "林福仁", "程式設計", "3", ""),
                    ("C", "黃老師", "服務設計", "1.5", ""),
                    ("D", "孫老師", "跨域學習", "2", "X-Class"),
                ]
            ],
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    @pytest.mark.parametrize(
        "params,expected_ids",
        [
            ({}, ["A", "B", "C", "D"]),
            ({"teacher": ""}, ["A", "B", "C", "D"]),
            ({"unknown": "ignored"}, ["A", "B", "C", "D"]),
            ({"teacher": "林福仁"}, ["A", "B"]),
            ({"chinese_title": "服務"}, ["A", "C"]),
            ({"teacher": "林福仁", "chinese_title": "服務"}, ["A"]),
            ({"type": "microcredits"}, ["A", "C"]),
            ({"type": "xclass"}, ["A", "D"]),
            ({"type": "xclass", "teacher": "林福仁"}, ["A"]),
            ({"type": "microcredits", "teacher": "林福仁"}, ["A"]),
            ({"type": "xclass", "teacher": "黃"}, []),
        ],
    )
    async def test_get_collection_filters(self, client, params, expected_ids):
        response = await client.get("/courses", params=params)
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == expected_ids
        assert response.headers["X-Total-Count"] == str(len(expected_ids))
        assert response.headers["X-Data-Commit-Hash"] == "course-test-version"
        assert not response.history

    @pytest.mark.parametrize("course_type", ["unknown", "", "XCLASS"])
    async def test_invalid_course_type(self, client, course_type):
        response = await client.get("/courses", params={"type": course_type})
        assert response.status_code == 422

    @pytest.mark.parametrize("course_type", ["microcredits", "xclass"])
    async def test_legacy_list_matches_type_filter(self, client, course_type):
        old = await client.get(f"/courses/lists/{course_type}")
        new = await client.get("/courses", params={"type": course_type})
        assert old.status_code == new.status_code == 200
        assert old.json() == new.json()
        assert old.headers["X-Total-Count"] == new.headers["X-Total-Count"]
        assert old.headers["X-Data-Commit-Hash"] == new.headers["X-Data-Commit-Hash"]

    async def test_legacy_all_courses_ignores_filters(self, client):
        response = await client.get("/courses/", params={"teacher": "absent"})
        assert response.status_code == 200
        assert [course["id"] for course in response.json()] == ["A", "B", "C", "D"]
        assert response.headers["X-Total-Count"] == "4"

    @pytest.mark.parametrize(
        "body,expected_ids",
        [
            (
                [
                    {"row_field": "teacher", "matcher": "黃", "regex_match": True},
                    "or",
                    {"row_field": "teacher", "matcher": "孫", "regex_match": True},
                ],
                ["C", "D"],
            ),
            ({"row_field": "teacher", "matcher": "林福仁"}, ["A", "B"]),
            ({"row_field": "teacher", "matcher": "林"}, []),
        ],
    )
    async def test_query_matches_legacy_search(self, client, body, expected_ids):
        old = await client.post("/courses/search", json=body)
        new = await client.post("/courses/query", json=body)
        assert old.status_code == new.status_code == 200
        assert [course["id"] for course in new.json()] == expected_ids
        assert old.json() == new.json()
        assert new.headers["X-Total-Count"] == str(len(expected_ids))
        assert new.headers["X-Data-Commit-Hash"] == "course-test-version"
