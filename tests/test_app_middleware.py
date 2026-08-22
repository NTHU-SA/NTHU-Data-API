"""Regression tests for middleware on the public composed ASGI application."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app


class TestPublicAppMiddleware:
    """The exported application must retain middleware configured for the REST API."""

    @pytest.fixture
    async def client(self):
        """Create an in-process client for the publicly exported ASGI application."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_public_app_answers_cors_preflight_requests(self, client: AsyncClient):
        """Browser clients can preflight a public API request from an allowed origin."""
        response = await client.options(
            "/openapi.json",
            headers={
                "Origin": "https://consumer.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"
        assert "GET" in response.headers["access-control-allow-methods"]

    async def test_public_app_keeps_cors_and_process_time_on_api_responses(
        self, client: AsyncClient
    ):
        """The composed app keeps CORS and timing middleware on actual API responses."""
        response = await client.get("/openapi.json", headers={"Origin": "https://consumer.example"})

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "*"
        assert float(response.headers["x-process-time"]) >= 0
