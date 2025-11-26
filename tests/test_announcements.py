"""Tests for announcements endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app


class TestAnnouncementsEndpoints:
    """Tests for announcements endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_announcements(self, client: AsyncClient):
        """Test getting all announcements."""
        response = await client.get("/announcements/")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "department",
        ["清華公佈欄", "國立清華大學學生會"],
    )
    async def test_get_announcements_by_department(self, client: AsyncClient, department: str):
        """Test getting announcements filtered by department."""
        params = {"department": department}
        response = await client.get("/announcements", params=params)
        assert response.status_code == 200

    async def test_get_announcements_sources(self, client: AsyncClient):
        """Test getting announcement sources."""
        response = await client.get("/announcements/sources")
        assert response.status_code == 200

    async def test_get_announcements_list_departments(self, client: AsyncClient):
        """Test listing announcement departments."""
        response = await client.get("/announcements/lists/departments")
        assert response.status_code == 200
