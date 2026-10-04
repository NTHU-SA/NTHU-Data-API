"""Tests for locations endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app

pytestmark = pytest.mark.usefixtures("dataset_runtime")


class TestLocationsEndpoints:
    """Tests for locations endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as client:
            yield client

    async def test_get_all_locations(self, client: AsyncClient):
        """Test getting all locations."""
        response = await client.get("/locations/")
        assert response.status_code == 200
        assert [location["name"] for location in response.json()] == [
            "校門",
            "綜合",
            "台積",
            "台達",
        ]
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    @pytest.mark.parametrize(
        "query,expected_names",
        [
            ("校門", ["校門"]),
            ("綜合", ["綜合"]),
            ("台積", ["台積", "台達"]),
            ("台達", ["台達", "台積"]),
        ],
    )
    async def test_search_locations_by_name(
        self, client: AsyncClient, query: str, expected_names: list[str]
    ):
        """Test searching locations by name."""
        response = await client.get("/locations/", params={"name": query})
        assert response.status_code == 200
        assert response.json() == [
            {"name": name, "latitude": "24.79", "longitude": "120.99"} for name in expected_names
        ]
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    @pytest.mark.parametrize("fuzzy", ["true", "false"])
    async def test_search_locations_no_matches(self, client: AsyncClient, fuzzy: str):
        response = await client.get("/locations/", params={"name": "nonexistent", "fuzzy": fuzzy})
        assert response.status_code == 200
        assert response.json() == []
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    @pytest.mark.parametrize("fuzzy", ["true", "false"])
    @pytest.mark.parametrize("name", [None, ""])
    async def test_empty_name_returns_all_locations(
        self, client: AsyncClient, fuzzy: str, name: str | None
    ):
        params = {"fuzzy": fuzzy}
        if name is not None:
            params["name"] = name
        response = await client.get("/locations/", params=params)
        unfiltered = await client.get("/locations/")
        assert response.status_code == 200
        assert response.json() == unfiltered.json()
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    async def test_explicit_fuzzy_search(self, client: AsyncClient):
        response = await client.get("/locations/", params={"name": "台積", "fuzzy": "true"})
        default = await client.get("/locations/", params={"name": "台積"})
        assert response.status_code == 200
        assert response.json() == default.json()

    async def test_exact_name_search(self, client: AsyncClient):
        response = await client.get("/locations/", params={"name": "台積", "fuzzy": "false"})
        assert response.status_code == 200
        assert response.json() == [{"name": "台積", "latitude": "24.79", "longitude": "120.99"}]
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    async def test_exact_search_does_not_match_substrings(self, client: AsyncClient):
        response = await client.get("/locations/", params={"name": "台", "fuzzy": "false"})
        assert response.status_code == 200
        assert response.json() == []
        fuzzy = await client.get("/locations/", params={"name": "台"})
        assert [location["name"] for location in fuzzy.json()] == ["台積", "台達"]

    async def test_invalid_fuzzy_parameter(self, client: AsyncClient):
        response = await client.get("/locations/", params={"name": "台積", "fuzzy": "invalid"})
        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["query", "fuzzy"]

    async def test_slashless_redirect_preserves_query(self, client: AsyncClient):
        response = await client.get("/locations", params={"name": "台積", "fuzzy": "false"})
        assert response.status_code == 307
        redirected = await client.get(response.headers["location"])
        assert redirected.status_code == 200
        assert redirected.json() == [{"name": "台積", "latitude": "24.79", "longitude": "120.99"}]

    async def test_legacy_search_locations(self, client: AsyncClient):
        response = await client.get("/locations/search", params={"query": "台積"})
        filtered = await client.get("/locations/", params={"name": "台積"})
        assert response.status_code == 200
        assert response.json() == filtered.json()
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    @pytest.mark.parametrize("query", ["nonexistent", ""])
    async def test_legacy_search_no_matches(self, client: AsyncClient, query: str):
        response = await client.get("/locations/search", params={"query": query})
        assert response.status_code == 404
        assert response.json() == {"detail": "Not found"}

    async def test_legacy_search_requires_query(self, client: AsyncClient):
        response = await client.get("/locations/search")
        assert response.status_code == 422


def test_locations_openapi():
    paths = app.openapi()["paths"]
    assert "/locations" not in paths
    operation = paths["/locations/"]["get"]
    assert operation["operationId"] == "getLocations"
    assert not operation.get("deprecated", False)
    assert "404" not in operation["responses"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "array"
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert parameters.keys() == {"name", "fuzzy"}
    for parameter in parameters.values():
        assert parameter["in"] == "query"
        assert not parameter["required"]
    assert parameters["fuzzy"]["schema"]["type"] == "boolean"
    assert parameters["fuzzy"]["schema"]["default"] is True
    assert paths["/locations/search"]["get"]["deprecated"] is True
    assert paths["/locations/search"]["get"]["operationId"] == "fuzzySearchLocations"
