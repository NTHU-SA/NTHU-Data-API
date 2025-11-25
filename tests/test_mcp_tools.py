"""Tests for MCP tools."""

import pytest

from data_api.mcp.server import (
    _find_dining,
    _get_announcements,
    _get_bus_stops,
    _get_energy_usage,
    _get_library_info,
    _get_newsletters,
    _get_next_buses,
    _search_campus,
    _search_courses,
)


class TestMCPTools:
    """Tests for MCP tools functionality."""

    @pytest.mark.asyncio
    async def test_search_campus(self):
        """Test campus search tool."""
        result = await _search_campus(query="教務處")
        assert "locations" in result
        assert "departments" in result
        assert "people" in result
        assert isinstance(result["locations"], list)
        assert isinstance(result["departments"], list)
        assert isinstance(result["people"], list)

    @pytest.mark.asyncio
    async def test_search_campus_location(self):
        """Test campus search for location."""
        result = await _search_campus(query="校門")
        assert "locations" in result
        assert isinstance(result["locations"], list)

    @pytest.mark.asyncio
    async def test_get_next_buses_default(self):
        """Test get next buses with default parameters."""
        result = await _get_next_buses()
        assert "current_time" in result
        assert "day_type" in result
        assert "buses" in result
        assert "route_info" in result
        assert isinstance(result["buses"], list)

    @pytest.mark.asyncio
    async def test_get_next_buses_main_route(self):
        """Test get next buses for main campus route."""
        result = await _get_next_buses(route="main", direction="up", limit=3)
        assert "buses" in result
        assert isinstance(result["buses"], list)

    @pytest.mark.asyncio
    async def test_get_next_buses_nanda_route(self):
        """Test get next buses for Nanda route."""
        result = await _get_next_buses(route="nanda", direction="down", limit=3)
        assert "buses" in result
        assert isinstance(result["buses"], list)

    @pytest.mark.asyncio
    async def test_search_courses_by_keyword(self):
        """Test course search by keyword."""
        result = await _search_courses(keyword="微積分", limit=5)
        assert "count" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)

    @pytest.mark.asyncio
    async def test_search_courses_by_teacher(self):
        """Test course search by teacher."""
        result = await _search_courses(teacher="王", limit=5)
        assert "count" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)

    @pytest.mark.asyncio
    async def test_search_courses_no_filter(self):
        """Test course search without filter returns all courses."""
        result = await _search_courses(limit=10)
        assert "count" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)

    @pytest.mark.asyncio
    async def test_get_announcements(self):
        """Test get announcements."""
        result = await _get_announcements(limit=5)
        assert "count" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)

    @pytest.mark.asyncio
    async def test_get_announcements_with_department(self):
        """Test get announcements with department filter."""
        result = await _get_announcements(department="學生", limit=5)
        assert "count" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)

    @pytest.mark.asyncio
    async def test_find_dining(self):
        """Test find dining without filters."""
        result = await _find_dining()
        assert "buildings" in result
        assert isinstance(result["buildings"], list)

    @pytest.mark.asyncio
    async def test_find_dining_by_building(self):
        """Test find dining by building."""
        result = await _find_dining(building="小吃部")
        assert "buildings" in result
        assert isinstance(result["buildings"], list)

    @pytest.mark.asyncio
    async def test_find_dining_check_open(self):
        """Test find dining with open check."""
        result = await _find_dining(check_open="today")
        assert "schedule" in result
        assert "open_restaurants" in result
        assert isinstance(result["open_restaurants"], list)

    @pytest.mark.asyncio
    async def test_get_library_info_space(self):
        """Test get library space info."""
        result = await _get_library_info(info_type="space")
        # Can either succeed or fail depending on external service
        assert "spaces" in result or "error" in result

    @pytest.mark.asyncio
    async def test_get_library_info_lost_and_found(self):
        """Test get library lost and found info."""
        result = await _get_library_info(info_type="lost_and_found")
        # Can either succeed or fail depending on external service
        assert "items" in result or "error" in result

    @pytest.mark.asyncio
    async def test_get_newsletters(self):
        """Test get newsletters."""
        result = await _get_newsletters()
        assert "count" in result
        assert "newsletters" in result
        assert isinstance(result["newsletters"], list)

    @pytest.mark.asyncio
    async def test_get_newsletters_with_search(self):
        """Test get newsletters with search."""
        result = await _get_newsletters(search="教務處")
        assert "count" in result
        assert "newsletters" in result
        assert isinstance(result["newsletters"], list)

    @pytest.mark.asyncio
    async def test_get_energy_usage(self):
        """Test get energy usage."""
        result = await _get_energy_usage()
        # Can either succeed or fail depending on external service
        assert "zones" in result or "error" in result

    @pytest.mark.asyncio
    async def test_get_bus_stops(self):
        """Test get bus stops."""
        result = await _get_bus_stops()
        assert "stops" in result
        assert isinstance(result["stops"], list)


class TestMCPToolIntegration:
    """Integration tests for MCP tools."""

    @pytest.mark.asyncio
    async def test_search_campus_returns_limited_results(self):
        """Test that campus search limits results appropriately."""
        result = await _search_campus(query="系")
        # Should return at most 5 locations, 5 departments, 10 people
        assert len(result["locations"]) <= 5
        assert len(result["departments"]) <= 5
        assert len(result["people"]) <= 10

    @pytest.mark.asyncio
    async def test_get_next_buses_respects_limit(self):
        """Test that bus results respect limit parameter."""
        result = await _get_next_buses(limit=3)
        assert len(result["buses"]) <= 3

    @pytest.mark.asyncio
    async def test_search_courses_respects_limit(self):
        """Test that course search respects limit parameter."""
        result = await _search_courses(limit=5)
        assert len(result["courses"]) <= 5

    @pytest.mark.asyncio
    async def test_course_search_result_format(self):
        """Test that course search returns expected fields."""
        result = await _search_courses(limit=1)
        if result["courses"]:
            course = result["courses"][0]
            expected_fields = [
                "id",
                "chinese_title",
                "english_title",
                "teacher",
                "credit",
                "time_and_room",
                "language",
            ]
            for field in expected_fields:
                assert field in course, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_announcements_result_format(self):
        """Test that announcements return expected structure."""
        result = await _get_announcements(limit=1)
        if result["sources"]:
            source = result["sources"][0]
            assert "department" in source
            assert "articles" in source
            if source["articles"]:
                article = source["articles"][0]
                assert "title" in article
                assert "link" in article
