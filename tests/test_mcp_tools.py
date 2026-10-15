"""Tests for MCP tools."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from conftest import course_payload
from fastmcp import Client
from httpx import Response
from pydantic import TypeAdapter

from data_api.domain.announcements import services as announcements_services
from data_api.domain.buses import services as buses_services
from data_api.domain.departments import services as departments_services
from data_api.domain.dining import services as dining_services
from data_api.domain.energy import services as energy_services
from data_api.domain.locations import services as locations_services
from data_api.domain.newsletters import services as newsletters_services
from data_api.mcp.server import mcp
from data_api.mcp.tools.announcements import _get_announcements
from data_api.mcp.tools.buses import _get_bus_schedule
from data_api.mcp.tools.courses import _search_courses
from data_api.mcp.tools.dining import _find_dining
from data_api.mcp.tools.directory import _search_directory
from data_api.mcp.tools.energy import _get_energy_usage
from data_api.mcp.tools.library import _get_library_info
from data_api.mcp.tools.locations import _search_locations
from data_api.mcp.tools.newsletters import _get_newsletters
from data_api.mcp.tools.result_types import (
    AnnouncementsResult,
    BusResult,
    CoursesResult,
    DiningBuildingsResult,
    DirectoryResult,
    EnergyResult,
    LibraryItemsResult,
    LibrarySpacesResult,
    LocationsResult,
    NewslettersResult,
)
from data_api.models.courses import CourseData
from data_api.runtime import get_runtime

pytestmark = pytest.mark.usefixtures("dataset_runtime")


class TestMCPTools:
    """Tests for MCP tools functionality."""

    async def test_search_directory(self):
        """Test directory search tool."""
        result = await _search_directory(query="教務處")
        assert set(result) == {"departments", "people"}
        assert "departments" in result
        assert "people" in result
        assert isinstance(result["departments"], list)
        assert isinstance(result["people"], list)

    async def test_search_locations(self):
        """Test location search."""
        result = await _search_locations(query="校門")
        assert set(result) == {"locations"}
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
        assert set(result) == {"buildings"}
        assert isinstance(result["buildings"], list)

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

    async def test_search_directory_returns_limited_results(self):
        """Test that directory search limits results appropriately."""
        result = await _search_directory(query="系")
        assert len(result["departments"]) <= 5
        assert len(result["people"]) <= 10

    async def test_search_locations_returns_limited_results(self):
        result = await _search_locations(query="館")
        assert len(result["locations"]) <= 5

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
            assert set(course) == set(CourseData.model_fields)
            CourseData.model_validate(course)

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


class TestRegisteredPayloads:
    """Exercise the private payload shapes through the registered MCP transport."""

    @pytest.mark.parametrize(
        ("name", "arguments", "result_type", "expected"),
        [
            (
                "search_directory",
                {"query": "not-found"},
                DirectoryResult,
                {
                    "departments": [],
                    "people": [],
                },
            ),
            ("search_locations", {"query": "not-found"}, LocationsResult, {"locations": []}),
            (
                "get_bus_schedule",
                {"day": "weekday"},
                BusResult,
                {
                    "buses": [],
                    "route_info": [],
                },
            ),
            (
                "search_courses",
                {"keyword": "not-found"},
                CoursesResult,
                {
                    "count": 0,
                    "courses": [],
                },
            ),
            (
                "get_announcements",
                {},
                AnnouncementsResult,
                {
                    "count": 0,
                    "sources": [],
                },
            ),
            ("find_dining", {}, DiningBuildingsResult, {"buildings": []}),
            (
                "find_dining",
                {"check_open": "weekday"},
                DiningBuildingsResult,
                {"buildings": []},
            ),
            (
                "get_newsletters",
                {"search": "not-found"},
                NewslettersResult,
                {
                    "count": 0,
                    "newsletters": [],
                },
            ),
        ],
    )
    async def test_empty_dataset_payloads(self, name, arguments, result_type, expected):
        async with Client(mcp) as client:
            response = await client.call_tool(name, arguments)
        assert not response.is_error
        TypeAdapter(result_type).validate_python(response.data)
        assert expected.items() <= response.data.items()

    async def test_nested_dataset_payloads_and_nulls(self, monkeypatch):
        monkeypatch.setattr(
            locations_services.locations_service,
            "fuzzy_search_locations",
            AsyncMock(
                return_value=(
                    "fixture",
                    [{"name": "Main gate", "latitude": "24.79", "longitude": "120.99"}],
                )
            ),
        )
        monkeypatch.setattr(
            departments_services.departments_service,
            "search_departments_and_people",
            AsyncMock(
                return_value=(
                    "fixture",
                    {
                        "departments": [
                            {
                                "index": "01",
                                "name": "Office",
                                "details": {"people": [{"name": "Alice", "title": None}]},
                            }
                        ],
                        "people": [{"name": "Alice", "title": None}],
                    },
                )
            ),
        )
        monkeypatch.setattr(
            announcements_services.announcements_service,
            "fuzzy_search_announcements",
            AsyncMock(
                return_value=(
                    "fixture",
                    [
                        {
                            "department": "Office",
                            "language": None,
                            "articles": [
                                {"title": "Notice", "link": "https://example.com", "date": None}
                            ],
                        }
                    ],
                )
            ),
        )
        monkeypatch.setattr(
            dining_services.dining_service,
            "fuzzy_search_dining_data",
            AsyncMock(
                return_value=(
                    "fixture",
                    [
                        {
                            "building": "Hall",
                            "restaurants": [
                                {
                                    "name": "Cafe",
                                    "phone": None,
                                    "schedule": {"weekday": "09:00-17:00"},
                                    "note": "",
                                }
                            ],
                        }
                    ],
                )
            ),
        )
        monkeypatch.setattr(
            newsletters_services.newsletters_service,
            "get_all_newsletters",
            AsyncMock(
                return_value=(
                    "fixture",
                    [
                        {
                            "name": "Newsletter",
                            "link": None,
                            "articles": [{"title": "Issue", "date": None}],
                        }
                    ],
                )
            ),
        )
        cases = [
            (
                "search_directory",
                {"query": "Alice"},
                DirectoryResult,
                {
                    "departments": [
                        {
                            "index": "01",
                            "name": "Office",
                            "details": {"people": [{"name": "Alice", "title": None}]},
                        }
                    ],
                    "people": [{"name": "Alice", "title": None}],
                },
            ),
            (
                "search_locations",
                {"query": "Main"},
                LocationsResult,
                {"locations": [{"name": "Main gate", "latitude": "24.79", "longitude": "120.99"}]},
            ),
            (
                "get_announcements",
                {},
                AnnouncementsResult,
                {
                    "count": 1,
                    "sources": [
                        {
                            "department": "Office",
                            "language": None,
                            "articles": [
                                {"title": "Notice", "link": "https://example.com", "date": None}
                            ],
                        }
                    ],
                },
            ),
            (
                "find_dining",
                {},
                DiningBuildingsResult,
                {
                    "buildings": [
                        {
                            "building": "Hall",
                            "restaurants": [
                                {
                                    "name": "Cafe",
                                    "phone": None,
                                    "schedule": {"weekday": "09:00-17:00"},
                                    "note": None,
                                }
                            ],
                        }
                    ],
                },
            ),
            (
                "find_dining",
                {"check_open": "weekday"},
                DiningBuildingsResult,
                {
                    "buildings": [
                        {
                            "building": "Hall",
                            "restaurants": [
                                {
                                    "name": "Cafe",
                                    "phone": None,
                                    "schedule": {"weekday": "09:00-17:00"},
                                    "note": None,
                                }
                            ],
                        }
                    ],
                },
            ),
            (
                "get_newsletters",
                {},
                NewslettersResult,
                {
                    "count": 1,
                    "newsletters": [
                        {
                            "name": "Newsletter",
                            "link": None,
                            "latest_articles": [{"title": "Issue", "date": None}],
                        }
                    ],
                },
            ),
        ]
        async with Client(mcp) as client:
            for name, arguments, result_type, expected in cases:
                response = await client.call_tool(name, arguments)
                assert not response.is_error
                assert response.data == expected
                TypeAdapter(result_type).validate_python(response.data)

    async def test_bus_simple_detailed_and_stop_payloads(self, monkeypatch):
        from data_api.domain.buses.enums import BusStopsName

        prepared = buses_services.BusesService.prepare(
            {
                "towardTSMCBuildingInfo": {
                    "direction": "up",
                    "duration": "2026",
                    "route": "main-up",
                    "routeEN": "Main up",
                },
                "weekdayBusScheduleTowardTSMCBuilding": [
                    {"time": "08:00", "description": "", "dep_stop": "校門", "line": "red"}
                ],
            }
        )
        monkeypatch.setattr(
            get_runtime(),
            "buses",
            SimpleNamespace(
                update_data=AsyncMock(),
                query_schedule=prepared.query_schedule,
                get_route_info=prepared.get_route_info,
                gen_bus_stops_info=prepared.gen_bus_stops_info,
            ),
        )
        async with Client(mcp) as client:
            for details in (False, True):
                response = await client.call_tool(
                    "get_bus_schedule",
                    {
                        "route": "main",
                        "direction": "up",
                        "day": "weekday",
                        "details": details,
                        "stop": BusStopsName.M1.value,
                    },
                )
                assert not response.is_error
                result = response.data
                TypeAdapter(BusResult).validate_python(result)
                assert result["route_info"] == [
                    {
                        "direction": "up",
                        "duration": "2026",
                        "route": "main-up",
                        "routeEN": "Main up",
                    }
                ]
                assert result["stop_name"] == BusStopsName.M1.value
                assert result["stop_info"][0]["name"] == BusStopsName.M1.value
                assert {"name_en", "latitude", "longitude"} <= result["stop_info"][0].keys()
                assert result["buses"]
                departure = result["buses"][0]["dep_info"] if details else result["buses"][0]
                assert departure["time"] == "08:00"
                assert departure["line"] == "main_red"
                if details:
                    assert {"stop", "arrive_time"} <= result["buses"][0]["stops_time"][0].keys()
                else:
                    assert "stops_time" not in result["buses"][0]

    async def test_course_payload_preserves_normalized_values(self):
        async with Client(mcp) as client:
            response = await client.call_tool("search_courses", {"limit": 1})
        assert not response.is_error
        TypeAdapter(CoursesResult).validate_python(response.data)
        assert response.data["count"] == 1
        assert response.data["courses"][0] == course_payload()

    async def test_live_payloads_and_empty_results(
        self,
        monkeypatch,
        mock_upstream,
        library_space_payload,
        lost_items_html,
        lost_items_empty_page,
    ):
        async with Client(mcp) as client:
            mock_upstream(lambda request: Response(200, json=library_space_payload))
            space = await client.call_tool("get_library_info", {"info_type": "space"})
            assert space.data == {
                "spaces": [
                    {
                        "zone": "Main library",
                        "type": "Study room",
                        "available": "12",
                    }
                ]
            }
            TypeAdapter(LibrarySpacesResult).validate_python(space.data)

            library_space_payload["rows"] = []
            empty_space = await client.call_tool("get_library_info", {"info_type": "space"})
            assert empty_space.data == {"spaces": []}

            mock_upstream(lambda request: Response(200, text=lost_items_html(1)))
            items = await client.call_tool("get_library_info", {"info_type": "lost_and_found"})
            assert items.data == {
                "items": [
                    {
                        "序號": "0",
                        "拾獲時間": "2026-09-30",
                        "拾獲地點": "Main library",
                        "描述": "Book title",
                    }
                ]
            }
            TypeAdapter(LibraryItemsResult).validate_python(items.data)

            mock_upstream(lambda request: Response(200, text=lost_items_empty_page))
            empty_items = await client.call_tool(
                "get_library_info", {"info_type": "lost_and_found"}
            )
            assert empty_items.data == {"items": []}

            mock_upstream(lambda request: Response(200, text='<img alt="kW: 0">'))
            energy = await client.call_tool("get_energy_usage", {})
            TypeAdapter(EnergyResult).validate_python(energy.data)
            assert len(energy.data["zones"]) == 3
            assert all(
                zone["usage_kw"] == 0 and zone["usage_percent"] == 0
                for zone in energy.data["zones"]
            )

            monkeypatch.setattr(
                energy_services.energy_service,
                "get_realtime_electricity_usage",
                AsyncMock(return_value=[]),
            )
            empty_energy = await client.call_tool("get_energy_usage", {})
            assert empty_energy.data == {"zones": []}
            TypeAdapter(EnergyResult).validate_python(empty_energy.data)
