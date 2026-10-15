"""3.0 retires legacy routes while retaining ordinary framework slash redirects."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app

REMOVED = [
    ("GET", "/departments"),
    ("GET", "/departments/"),
    ("GET", "/departments/search"),
    ("GET", "/announcements/lists/departments"),
    ("GET", "/courses/search"),
    ("POST", "/courses/search"),
    ("GET", "/courses/lists/microcredits"),
    ("GET", "/newsletters/NTHU-Newsletter"),
    ("GET", "/locations/search"),
    ("GET", "/buses/info/stops"),
    ("GET", "/buses/schedules"),
    ("GET", "/buses/stops/校門"),
    ("GET", "/libraries/space"),
    ("GET", "/libraries/lost_and_found"),
    ("GET", "/energy/electricity_usage"),
]


@pytest.mark.parametrize("method,path", REMOVED)
async def test_retired_routes_are_not_served(method, path):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as client:
        response = await client.request(method, path)
    assert response.status_code == 404
    assert "location" not in response.headers


def test_only_current_routes_are_registered():
    paths = app.openapi()["paths"]
    assert all(not path.endswith("/") for path in paths)
    assert all(
        not operation.get("deprecated", False)
        for methods in paths.values()
        for operation in methods.values()
    )
