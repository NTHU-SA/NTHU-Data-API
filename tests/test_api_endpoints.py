"""Tests for API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app

pytestmark = pytest.mark.usefixtures("dataset_runtime")


ROOT_ENDPOINTS = [
    ("/announcements", "getAnnouncements", {"title": "Notice", "fuzzy": "false"}),
    ("/calendars", "getAllCalendars", {}),
    ("/dining", "getDiningData", {"restaurant_name": "Test", "fuzzy": "false"}),
    ("/locations", "getLocations", {"name": "台積", "fuzzy": "false"}),
    ("/newsletters", "getAllNewsletters", {"name": "Test", "fuzzy": "false"}),
]


@pytest.mark.parametrize("path,operation_id,params", ROOT_ENDPOINTS)
async def test_root_endpoints_and_slash_redirects(path, operation_id, params):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as client:
        response = await client.get(path, params=params)
        legacy = await client.get(f"{path}/", params=params)

    assert response.status_code == 200
    assert legacy.status_code == 307
    assert "location" not in response.headers
    assert legacy.headers["location"].split("?")[0] == f"http://test{path}"
    assert response.headers["X-Data-Commit-Hash"]


@pytest.mark.parametrize("path,operation_id,params", ROOT_ENDPOINTS)
def test_root_endpoints_openapi_migration(path, operation_id, params):
    paths = app.openapi()["paths"]
    operation = paths[path]["get"]
    assert f"{path}/" not in paths
    assert operation["operationId"] == operation_id
    assert not operation.get("deprecated", False)


def test_openapi_operation_ids_are_unique():
    operations = [
        operation["operationId"]
        for path in app.openapi()["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
    ]
    assert len(operations) == len(set(operations))


class TestAnnouncementsEndpoints:
    """Tests for announcements endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_announcements_with_title_filter(self, client: AsyncClient):
        """Test filtering announcements by title."""
        params = {"title": "公告"}
        response = await client.get("/announcements", params=params)
        assert response.status_code == 200

    async def test_announcements_with_fuzzy_search(self, client: AsyncClient):
        """Test fuzzy search for announcements."""
        params = {"department": "學生", "fuzzy": True}
        response = await client.get("/announcements", params=params)
        assert response.status_code == 200

    async def test_announcements_sources(self, client: AsyncClient):
        """Test getting announcement sources."""
        response = await client.get("/announcements/sources")
        assert response.status_code == 200

    async def test_announcements_sources_with_department(self, client: AsyncClient):
        """Test getting announcement sources with department filter."""
        params = {"department": "清華公佈欄"}
        response = await client.get("/announcements/sources", params=params)
        assert response.status_code == 200


class TestDiningEndpoints:
    """Tests for dining endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_dining_with_restaurant_name(self, client: AsyncClient):
        """Test filtering dining by restaurant name."""
        params = {"restaurant_name": "麥當勞"}
        response = await client.get("/dining", params=params)
        assert response.status_code == 200

    async def test_dining_with_building_name(self, client: AsyncClient):
        """Test filtering dining by building name."""
        params = {"building_name": "小吃部"}
        response = await client.get("/dining", params=params)
        assert response.status_code == 200

    async def test_dining_fuzzy_search(self, client: AsyncClient):
        """Test dining fuzzy search."""
        params = {"restaurant_name": "便利", "fuzzy": True}
        response = await client.get("/dining", params=params)
        assert response.status_code == 200


class TestLocationsEndpoints:
    """Tests for locations endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_locations_all(self, client: AsyncClient):
        """Test getting all locations."""
        response = await client.get("/locations")
        assert response.status_code == 200


class TestNewslettersEndpoints:
    """Tests for newsletters endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_newsletters_all(self, client: AsyncClient):
        """Test getting all newsletters."""
        response = await client.get("/newsletters")
        assert response.status_code == 200


class TestCoursesEndpoints:
    """Tests for courses endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_courses_all(self, client: AsyncClient):
        """Test getting all courses."""
        response = await client.get("/courses")
        assert response.status_code == 200

    async def test_courses_search_with_params(self, client: AsyncClient):
        """Test searching courses with parameters."""
        params = {"chinese_title": "微積分"}
        response = await client.get("/courses", params=params)
        assert response.status_code == 200


class TestBusesEndpoints:
    """Tests for buses endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_buses_routes_basic(self, client: AsyncClient):
        """Test basic bus routes."""
        response = await client.get("/buses/routes/")
        assert response.status_code == 200

    async def test_buses_routes_with_params(self, client: AsyncClient):
        """Test bus routes with parameters."""
        response = await client.get("/buses/routes/?route=main&direction=up")
        assert response.status_code == 200

    async def test_buses_routes_nanda(self, client: AsyncClient):
        """Test Nanda bus routes."""
        response = await client.get("/buses/routes/?route=nanda&direction=up")
        assert response.status_code == 200


class TestDirectoryEndpoints:
    """Tests for directory endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_directory_search_multiple_keywords(self, client: AsyncClient):
        """Test directory search with different keywords."""
        queries = ["教務處", "學務處", "研發處"]
        for query in queries:
            params = {"query": query}
            response = await client.get("/directory", params=params)
            assert response.status_code == 200


@pytest.mark.parametrize(
    "path,statuses",
    [
        ("/buses/routes", {"500"}),
        ("/buses/stops", {"500"}),
        ("/energy/electricity", {"500", "502", "504"}),
        ("/courses", {"422"}),
        ("/libraries/spaces", {"500", "502", "504"}),
        ("/libraries/lost-and-found", {"500", "502", "504"}),
        ("/libraries/rss/{rss_type}", {"404"}),
        ("/calendars/{calendar_id}", {"404"}),
        ("/calendars/{calendar_id}/events", {"400", "404"}),
        ("/calendars/{calendar_id}/events/{event_id}", {"404"}),
    ],
)
def test_openapi_documents_route_errors(path, statuses):
    responses = app.openapi()["paths"][path]["get"]["responses"]
    assert statuses <= responses.keys()


@pytest.mark.parametrize(
    "path",
    [
        "/energy/electricity",
        "/libraries/spaces",
        "/libraries/lost-and-found",
    ],
)
def test_openapi_live_errors_have_detail_schema(path):
    schema = app.openapi()
    responses = schema["paths"][path]["get"]["responses"]
    assert "403" not in responses
    assert "404" not in responses
    for status in ["500", "502", "504"]:
        assert responses[status]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }
    error_schema = schema["components"]["schemas"]["ErrorResponse"]
    assert error_schema["required"] == ["detail"]
    assert error_schema["properties"]["detail"]["type"] == "string"
