"""Tests for energy endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient, Response

from data_api.api.api import app
from data_api.domain.energy.services import ELECTRICITY_USAGE_DATA


class TestEnergyEndpoints:
    """Tests for energy endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_electricity_usage(self, client: AsyncClient, mock_upstream):
        values = {1: 1234, 2: 0, 3: -1}

        def handler(request):
            system_id = int(request.url.path.removesuffix(".aspx")[-1])
            return Response(200, text=f'<img alt="kW: {values[system_id]:,}">')

        mock_upstream(handler)
        response = await client.get("/energy/electricity_usage")
        assert response.status_code == 200
        for item, system in zip(response.json(), ELECTRICITY_USAGE_DATA, strict=True):
            assert item == {
                "name": system["name"],
                "data": values[system["id"]],
                "capacity": system["capacity"],
                "unit": "kW",
                "last_updated": item["last_updated"],
            }
            assert item["last_updated"]

    async def test_upstream_unavailable(self, client: AsyncClient):
        response = await client.get("/energy/electricity_usage")
        assert response.status_code == 502
        assert response.json() == {"detail": "Upstream service unavailable"}
