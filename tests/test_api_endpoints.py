"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from data_api.api.api import app

client = TestClient(app)


class TestAnnouncementsEndpoints:
    """Tests for announcements endpoints."""

    def test_announcements_with_title_filter(self):
        """Test filtering announcements by title."""
        params = {"title": "公告"}
        response = client.get(url="/announcements", params=params)
        assert response.status_code == 200

    def test_announcements_with_fuzzy_search(self):
        """Test fuzzy search for announcements."""
        params = {"department": "學生", "fuzzy": True}
        response = client.get(url="/announcements", params=params)
        assert response.status_code == 200

    def test_announcements_sources(self):
        """Test getting announcement sources."""
        response = client.get(url="/announcements/sources")
        assert response.status_code == 200

    def test_announcements_sources_with_department(self):
        """Test getting announcement sources with department filter."""
        params = {"department": "清華公佈欄"}
        response = client.get(url="/announcements/sources", params=params)
        assert response.status_code == 200

    def test_announcements_list_departments(self):
        """Test listing announcement departments."""
        response = client.get(url="/announcements/lists/departments")
        assert response.status_code == 200


class TestDiningEndpoints:
    """Tests for dining endpoints."""

    def test_dining_with_restaurant_name(self):
        """Test filtering dining by restaurant name."""
        params = {"restaurant_name": "麥當勞"}
        response = client.get(url="/dining", params=params)
        assert response.status_code == 200

    def test_dining_with_building_name(self):
        """Test filtering dining by building name."""
        params = {"building_name": "小吃部"}
        response = client.get(url="/dining", params=params)
        assert response.status_code == 200

    def test_dining_fuzzy_search(self):
        """Test dining fuzzy search."""
        params = {"restaurant_name": "便利", "fuzzy": True}
        response = client.get(url="/dining", params=params)
        assert response.status_code == 200


class TestLocationsEndpoints:
    """Tests for locations endpoints."""

    def test_locations_all(self):
        """Test getting all locations."""
        response = client.get(url="/locations")
        assert response.status_code == 200


class TestNewslettersEndpoints:
    """Tests for newsletters endpoints."""

    def test_newsletters_all(self):
        """Test getting all newsletters."""
        response = client.get(url="/newsletters/")
        assert response.status_code == 200


class TestCoursesEndpoints:
    """Tests for courses endpoints."""

    def test_courses_all(self):
        """Test getting all courses."""
        response = client.get(url="/courses/")
        assert response.status_code == 200

    def test_courses_search_with_params(self):
        """Test searching courses with parameters."""
        params = {"chinese_title": "微積分"}
        response = client.get(url="/courses/search", params=params)
        assert response.status_code == 200


class TestBusesEndpoints:
    """Tests for buses endpoints."""

    def test_buses_routes_basic(self):
        """Test basic bus routes."""
        response = client.get(url="/buses/routes/")
        assert response.status_code == 200

    def test_buses_routes_with_params(self):
        """Test bus routes with parameters."""
        response = client.get(
            url="/buses/routes/?bus_type=main&direction=up"
        )
        assert response.status_code == 200

    def test_buses_routes_nanda(self):
        """Test Nanda bus routes."""
        response = client.get(
            url="/buses/routes/?bus_type=nanda&direction=up"
        )
        assert response.status_code == 200


class TestDepartmentsEndpoints:
    """Tests for departments endpoints."""

    def test_departments_search_multiple_keywords(self):
        """Test departments search with different keywords."""
        queries = ["教務處", "學務處", "研發處"]
        for query in queries:
            params = {"query": query}
            response = client.get(url="/departments/search/", params=params)
            assert response.status_code == 200
