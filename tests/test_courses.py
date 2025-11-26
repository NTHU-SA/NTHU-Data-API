"""Tests for courses endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app


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
