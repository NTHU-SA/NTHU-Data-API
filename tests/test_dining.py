"""Tests for dining endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app


class TestDiningEndpoints:
    """Tests for dining endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_dining(self, client: AsyncClient):
        """Test getting all dining information."""
        response = await client.get("/dining")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "building_name",
        [_.value for _ in schemas.dining.DiningBuildingName],
    )
    async def test_get_dining_by_building(self, client: AsyncClient, building_name: str):
        """Test getting dining information filtered by building."""
        params = {"building_name": building_name}
        response = await client.get("/dining", params=params)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "schedule",
        [_.value for _ in schemas.dining.DiningScheduleName],
    )
    async def test_get_open_restaurants(self, client: AsyncClient, schedule: str):
        """Test getting open restaurants by schedule."""
        params = {"schedule": schedule}
        response = await client.get("/dining/open", params=params)
        assert response.status_code == 200
