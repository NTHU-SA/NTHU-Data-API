"""Tests for MCP tools."""

import pytest
from httpx import Response

from data_api.mcp.tools.announcements import _get_announcements
from data_api.mcp.tools.buses import _get_bus_schedule
from data_api.mcp.tools.campus import _search_campus
from data_api.mcp.tools.courses import _search_courses
from data_api.mcp.tools.dining import _find_dining
from data_api.mcp.tools.energy import _get_energy_usage
from data_api.mcp.tools.library import _get_library_info
from data_api.mcp.tools.newsletters import _get_newsletters

pytestmark = pytest.mark.usefixtures("dataset_runtime")


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

    async def test_get_bus_schedule_default(self):
        """Test bus schedules with default parameters."""
        result = await _get_bus_schedule()
        assert "current_time" in result
        assert "day_type" in result
        assert "buses" in result
        assert "route_info" in result
        assert isinstance(result["buses"], list)

    async def test_get_bus_schedule_main_route(self):
        """Test schedules for the main campus route."""
        result = await _get_bus_schedule(route="main", direction="up", limit=3)
        assert "buses" in result
        assert isinstance(result["buses"], list)

    async def test_get_bus_schedule_nanda_route(self):
        """Test schedules for the Nanda route."""
        result = await _get_bus_schedule(route="nanda", direction="down", limit=3)
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

    @pytest.mark.parametrize("empty", [False, True])
    async def test_get_library_info_space(self, mock_upstream, library_space_payload, empty):
        if empty:
            library_space_payload["rows"] = []
        mock_upstream(lambda request: Response(200, json=library_space_payload))
        result = await _get_library_info(info_type="space")
        assert result == {
            "spaces": (
                [] if empty else [{"zone": "Main library", "type": "Study room", "available": "12"}]
            )
        }

    @pytest.mark.parametrize("count", [0, 12])
    async def test_get_library_info_lost_and_found(self, mock_upstream, lost_items_html, count):
        mock_upstream(lambda request: Response(200, text=lost_items_html(count)))
        result = await _get_library_info(info_type="lost_and_found")
        assert result == {
            "items": [
                {
                    "序號": str(index),
                    "拾獲時間": "2026-09-30",
                    "拾獲地點": "Main library",
                    "描述": "Book title",
                }
                for index in range(min(count, 10))
            ]
        }

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

    async def test_get_energy_usage(self, mock_upstream):
        mock_upstream(lambda request: Response(200, text='<img alt="kW: 0">'))
        result = await _get_energy_usage()
        assert len(result["zones"]) == 3
        for zone in result["zones"]:
            assert set(zone) == {
                "name",
                "usage_kw",
                "capacity_kw",
                "usage_percent",
                "last_updated",
            }
            assert zone["usage_kw"] == 0
            assert zone["usage_percent"] == 0

    async def test_get_bus_schedule_with_stop(self):
        """Test schedule queries include the selected stop's metadata."""
        from data_api.domain.buses.enums import BusStopsName

        result = await _get_bus_schedule(stop=BusStopsName.M1)
        assert "stop_info" in result
        assert "stop_name" in result
        assert result["stop_name"] == "北校門口"
        assert "current_time" in result
        assert "day_type" in result
        assert "buses" in result
        assert isinstance(result["buses"], list)

    async def test_get_bus_schedule_with_stop_name_string(self):
        """Test MCP converts a stop name string to its enum."""
        from fastmcp import Client

        from data_api.mcp.server import mcp

        async with Client(mcp) as client:
            response = await client.call_tool("get_bus_schedule", {"stop": "台積館"})
        result = response.data
        assert "stop_info" in result
        assert "stop_name" in result
        assert "buses" in result
        assert isinstance(result["buses"], list)


class TestMCPToolIntegration:
    """Integration tests for MCP tools."""

    async def test_search_campus_returns_limited_results(self):
        """Test that campus search limits results appropriately."""
        result = await _search_campus(query="系")
        # Should return at most 5 locations, 5 departments, 10 people
        assert len(result["locations"]) <= 5
        assert len(result["departments"]) <= 5
        assert len(result["people"]) <= 10

    async def test_get_bus_schedule_respects_limit(self):
        """Test that bus results respect limit parameter."""
        result = await _get_bus_schedule(limit=3)
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

    async def test_get_bus_schedule_with_stop_respects_limit(self):
        """Test that stop-filtered schedules respect the limit."""
        from data_api.domain.buses.enums import BusStopsName

        result = await _get_bus_schedule(stop=BusStopsName.M1, limit=2)
        assert len(result["buses"]) <= 2
