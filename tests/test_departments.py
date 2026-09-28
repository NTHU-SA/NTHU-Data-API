"""Tests for departments endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.data.manager import nthudata
from data_api.domain.departments.services import departments_service

pytestmark = pytest.mark.usefixtures("dataset_runtime")


class TestDepartmentsEndpoints:
    """Tests for departments endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_departments(self, client: AsyncClient):
        """Test getting all departments."""
        response = await client.get("/departments/")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "query",
        ["校長", "高為元", "總務處"],
    )
    async def test_search_departments(self, client: AsyncClient, query: str):
        """Test searching departments with various queries."""
        params = {"query": query}
        response = await client.get("/departments/search/", params=params)
        assert response.status_code == 200


@pytest.mark.parametrize("metadata", [{}, {"title": None}, {"title": ""}])
async def test_search_handles_missing_optional_person_title(monkeypatch, metadata):
    async def get_directory(endpoint):
        return "test", [
            {"name": "Directory", "details": {"people": [{"name": "Alice", **metadata}]}}
        ]

    monkeypatch.setattr(nthudata, "get", get_directory)
    commit, result = await departments_service.fuzzy_search_departments_and_people("ZZZ")
    assert commit == "test"
    assert result == {"departments": [], "people": []}
