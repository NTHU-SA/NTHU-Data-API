"""Tests for newsletters endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app


class TestNewslettersEndpoints:
    """Tests for newsletters endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_newsletters(self, client: AsyncClient):
        """Test getting all newsletters."""
        response = await client.get("/newsletters/")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "newsletter_name",
        [_.value for _ in schemas.newsletters.NewsletterName],
    )
    async def test_get_newsletter_by_name(self, client: AsyncClient, newsletter_name: str):
        """Test getting newsletter by name."""
        response = await client.get(f"/newsletters/{newsletter_name}")
        assert response.status_code == 200
