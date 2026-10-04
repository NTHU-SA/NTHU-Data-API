"""Tests for API endpoints."""

from copy import deepcopy

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app

pytestmark = pytest.mark.usefixtures("dataset_runtime")


ROOT_ENDPOINTS = [
    ("/announcements", "getAnnouncements", {"title": "Notice", "fuzzy": "false"}),
    ("/calendars", "getAllCalendars", {}),
    ("/departments", "getAllDepartments", {}),
    ("/dining", "getDiningData", {"restaurant_name": "Test", "fuzzy": "false"}),
    ("/locations", "getLocations", {"name": "台積", "fuzzy": "false"}),
    ("/newsletters", "getAllNewsletters", {"name": "Test", "fuzzy": "false"}),
]


@pytest.mark.parametrize("path,operation_id,params", ROOT_ENDPOINTS)
async def test_root_endpoints_preserve_legacy_responses(path, operation_id, params):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as client:
        response = await client.get(path, params=params)
        legacy = await client.get(f"{path}/", params=params)

    assert response.status_code == legacy.status_code == 200
    assert "location" not in response.headers
    assert "location" not in legacy.headers
    assert response.json() == legacy.json()
    assert response.headers["X-Data-Commit-Hash"] == legacy.headers["X-Data-Commit-Hash"]


@pytest.mark.parametrize("path,operation_id,params", ROOT_ENDPOINTS)
def test_root_endpoints_openapi_migration(path, operation_id, params):
    paths = app.openapi()["paths"]
    operation = paths[path]["get"]
    legacy = paths[f"{path}/"]["get"]
    assert operation["operationId"] == operation_id
    assert not operation.get("deprecated", False)
    assert legacy["deprecated"] is True
    assert legacy["operationId"] == f"{operation_id}Deprecated"
    assert f"GET {path}" in legacy["description"]
    assert operation.get("parameters", []) == legacy.get("parameters", [])
    responses = deepcopy(operation["responses"])
    legacy_responses = deepcopy(legacy["responses"])
    for documented in [responses, legacy_responses]:
        documented["200"]["content"]["application/json"]["schema"].pop("title", None)
    assert responses == legacy_responses


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
        response = await client.get("/newsletters/")
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
        response = await client.get("/courses/")
        assert response.status_code == 200

    async def test_courses_search_with_params(self, client: AsyncClient):
        """Test searching courses with parameters."""
        params = {"chinese_title": "微積分"}
        response = await client.get("/courses/search", params=params)
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


class TestDepartmentsEndpoints:
    """Tests for departments endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_departments_search_multiple_keywords(self, client: AsyncClient):
        """Test departments search with different keywords."""
        queries = ["教務處", "學務處", "研發處"]
        for query in queries:
            params = {"query": query}
            response = await client.get("/departments/search/", params=params)
            assert response.status_code == 200


@pytest.mark.parametrize(
    "path,statuses",
    [
        ("/buses/routes", {"500"}),
        ("/buses/stops", {"500"}),
        ("/buses/info/stops", {"500"}),
        ("/buses/schedules", {"500"}),
        ("/energy/electricity", {"500", "502", "504"}),
        ("/energy/electricity_usage", {"500", "502", "504"}),
        ("/courses/search", {"422"}),
        ("/locations/search", {"404"}),
        ("/newsletters/{newsletter_name}", {"404"}),
        ("/libraries/space", {"500", "502", "504"}),
        ("/libraries/spaces", {"500", "502", "504"}),
        ("/libraries/lost-and-found", {"500", "502", "504"}),
        ("/libraries/lost_and_found", {"500", "502", "504"}),
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
        "/energy/electricity_usage",
        "/libraries/space",
        "/libraries/spaces",
        "/libraries/lost-and-found",
        "/libraries/lost_and_found",
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


@pytest.mark.parametrize(
    "legacy_path,path,legacy_operation_id,operation_id",
    [
        (
            "/libraries/space",
            "/libraries/spaces",
            "getLibrarySpaceAvailability",
            "getLibrarySpaces",
        ),
        (
            "/energy/electricity_usage",
            "/energy/electricity",
            "getRealtimeElectricityUsage",
            "getElectricity",
        ),
        (
            "/libraries/lost_and_found",
            "/libraries/lost-and-found",
            "getLibraryLostAndFoundItems",
            "getLibraryLostAndFound",
        ),
    ],
)
def test_openapi_live_route_migration(legacy_path, path, legacy_operation_id, operation_id):
    paths = app.openapi()["paths"]
    legacy = paths[legacy_path]["get"]
    current = paths[path]["get"]
    assert legacy["deprecated"] is True
    assert path in legacy["description"]
    assert not current.get("deprecated", False)
    assert legacy["operationId"] == legacy_operation_id
    assert current["operationId"] == operation_id
    assert legacy["responses"].keys() == current["responses"].keys()
    for status in legacy["responses"]:
        if status == "200":
            legacy_schema = legacy["responses"][status]["content"]["application/json"]["schema"]
            current_schema = current["responses"][status]["content"]["application/json"]["schema"]
            assert {key: value for key, value in legacy_schema.items() if key != "title"} == {
                key: value for key, value in current_schema.items() if key != "title"
            }
        else:
            assert legacy["responses"][status] == current["responses"][status]
    operation_ids = [
        operation["operationId"]
        for path_item in paths.values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]
    assert len(operation_ids) == len(set(operation_ids))
