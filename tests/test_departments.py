"""Tests for departments endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app


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
