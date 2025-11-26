"""Tests for locations endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app


class TestLocationsEndpoints:
    """Tests for locations endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_locations(self, client: AsyncClient):
        """Test getting all locations."""
        response = await client.get("/locations")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "query",
        ["校門", "綜合", "台積", "台達"],
    )
    async def test_search_locations_by_name(self, client: AsyncClient, query: str):
        """Test searching locations by name."""
        params = {"query": query}
        response = await client.get("/locations/search", params=params)
        assert response.status_code == 200
