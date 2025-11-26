"""Tests for API endpoints."""

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

    async def test_announcements_list_departments(self, client: AsyncClient):
        """Test listing announcement departments."""
        response = await client.get("/announcements/lists/departments")
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
        response = await client.get("/buses/routes/?bus_type=main&direction=up")
        assert response.status_code == 200

    async def test_buses_routes_nanda(self, client: AsyncClient):
        """Test Nanda bus routes."""
        response = await client.get("/buses/routes/?bus_type=nanda&direction=up")
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
