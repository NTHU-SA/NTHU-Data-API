"""Tests for MCP tools."""

from data_api.mcp.tools.announcements import _get_announcements
from data_api.mcp.tools.buses import _get_bus_stops, _get_next_buses
from data_api.mcp.tools.campus import _search_campus
from data_api.mcp.tools.courses import _search_courses
from data_api.mcp.tools.dining import _find_dining
from data_api.mcp.tools.energy import _get_energy_usage
from data_api.mcp.tools.library import _get_library_info
from data_api.mcp.tools.newsletters import _get_newsletters


class TestMCPTools:
    """Tests for MCP tools functionality."""

    async def test_search_campus(self):
        """Test campus search tool."""
        result = await _search_campus(query="教務處")
        assert "locations" in result
        assert "departments" in result
        assert "people" in result
        assert isinstance(result["locations"], list)
        assert isinstance(result["departments"], list)
        assert isinstance(result["people"], list)

    async def test_search_campus_location(self):
        """Test campus search for location."""
        result = await _search_campus(query="校門")
        assert "locations" in result
        assert isinstance(result["locations"], list)

    async def test_get_next_buses_default(self):
        """Test get next buses with default parameters."""
        result = await _get_next_buses()
        assert "current_time" in result
        assert "day_type" in result
        assert "buses" in result
        assert "route_info" in result
        assert isinstance(result["buses"], list)

    async def test_get_next_buses_main_route(self):
        """Test get next buses for main campus route."""
        result = await _get_next_buses(route="main", direction="up", limit=3)
        assert "buses" in result
        assert isinstance(result["buses"], list)

    async def test_get_next_buses_nanda_route(self):
        """Test get next buses for Nanda route."""
        result = await _get_next_buses(route="nanda", direction="down", limit=3)
        assert "buses" in result
        assert isinstance(result["buses"], list)

    async def test_search_courses_by_keyword(self):
        """Test course search by keyword."""
        result = await _search_courses(keyword="微積分", limit=5)
        assert "count" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)

    async def test_search_courses_by_teacher(self):
        """Test course search by teacher."""
        result = await _search_courses(teacher="王", limit=5)
        assert "count" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)

    async def test_search_courses_no_filter(self):
        """Test course search without filter returns all courses."""
        result = await _search_courses(limit=10)
        assert "count" in result
        assert "courses" in result
        assert isinstance(result["courses"], list)

    async def test_get_announcements(self):
        """Test get announcements."""
        result = await _get_announcements(limit=5)
        assert "count" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)

    async def test_get_announcements_with_department(self):
        """Test get announcements with department filter."""
        result = await _get_announcements(department="學生", limit=5)
        assert "count" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)

    async def test_find_dining(self):
        """Test find dining without filters."""
        result = await _find_dining()
        assert "buildings" in result
        assert isinstance(result["buildings"], list)

    async def test_find_dining_by_building(self):
        """Test find dining by building."""
        result = await _find_dining(building="小吃部")
        assert "buildings" in result
        assert isinstance(result["buildings"], list)

    async def test_find_dining_check_open(self):
        """Test find dining with open check."""
        result = await _find_dining(check_open="today")
        assert "schedule" in result
        assert "open_restaurants" in result
        assert isinstance(result["open_restaurants"], list)

    async def test_get_library_info_space(self):
        """Test get library space info."""
        result = await _get_library_info(info_type="space")
        # Can either succeed or fail depending on external service
        assert "spaces" in result or "error" in result

    async def test_get_library_info_lost_and_found(self):
        """Test get library lost and found info."""
        result = await _get_library_info(info_type="lost_and_found")
        # Can either succeed or fail depending on external service
        assert "items" in result or "error" in result

    async def test_get_newsletters(self):
        """Test get newsletters."""
        result = await _get_newsletters()
        assert "count" in result
        assert "newsletters" in result
        assert isinstance(result["newsletters"], list)

    async def test_get_newsletters_with_search(self):
        """Test get newsletters with search."""
        result = await _get_newsletters(search="教務處")
        assert "count" in result
        assert "newsletters" in result
        assert isinstance(result["newsletters"], list)

    async def test_get_energy_usage(self):
        """Test get energy usage."""
        result = await _get_energy_usage()
        # Can either succeed or fail depending on external service
        assert "zones" in result or "error" in result

    async def test_get_bus_stops(self):
        """Test get bus stops with specific stop_name to get upcoming buses."""
        from data_api.domain.buses.enums import BusStopsName

        result = await _get_bus_stops(stop_name=BusStopsName.M1)
        assert "stop_info" in result
        assert "stop_name" in result
        assert result["stop_name"] == "北校門口"
        assert "current_time" in result
        assert "day_type" in result
        assert "upcoming_buses" in result
        assert isinstance(result["upcoming_buses"], list)

    async def test_get_bus_stops_with_stop_name_string(self):
        """Test get bus stops with stop_name as string."""
        result = await _get_bus_stops(stop_name="台積館")
        assert "stop_info" in result
        assert "stop_name" in result
        assert "upcoming_buses" in result
        assert isinstance(result["upcoming_buses"], list)


class TestMCPToolIntegration:
    """Integration tests for MCP tools."""

    async def test_search_campus_returns_limited_results(self):
        """Test that campus search limits results appropriately."""
        result = await _search_campus(query="系")
        # Should return at most 5 locations, 5 departments, 10 people
        assert len(result["locations"]) <= 5
        assert len(result["departments"]) <= 5
        assert len(result["people"]) <= 10

    async def test_get_next_buses_respects_limit(self):
        """Test that bus results respect limit parameter."""
        result = await _get_next_buses(limit=3)
        assert len(result["buses"]) <= 3

    async def test_search_courses_respects_limit(self):
        """Test that course search respects limit parameter."""
        result = await _search_courses(limit=5)
        assert len(result["courses"]) <= 5

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

    async def test_get_bus_stops_upcoming_buses_respects_limit(self):
        """Test that bus stops upcoming buses respects limit parameter."""
        from data_api.domain.buses.enums import BusStopsName

        result = await _get_bus_stops(stop_name=BusStopsName.M1, limit=2)
        assert len(result.get("upcoming_buses", [])) <= 2
