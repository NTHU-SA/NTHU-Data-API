"""Tests for bus graph module."""

import pytest

from data_api.domain.buses import graph, models


class TestStopsData:
    """Tests for stop definitions."""

    def test_stops_data_exists(self):
        """Test that stops data is defined."""
        assert len(graph.STOPS_DATA) > 0

    def test_stop_has_required_fields(self):
        """Test that stops have required fields."""
        for stop_id, stop in graph.STOPS_DATA.items():
            assert isinstance(stop, models.Stop)
            assert stop.id == stop_id
            assert stop.name
            assert stop.name_en
            assert stop.latitude
            assert stop.longitude


class TestCreateRoute:
    """Tests for route creation."""

    def test_create_route(self):
        """Test creating a route."""
        route = graph.create_route("test_route", ["M1", "M2", "M3"], [0, 1, 2])
        assert route.id == "test_route"
        assert len(route.stops) == 3
        assert len(route.time_offsets) == 3
        assert route.time_offsets == [0, 1, 3]

    def test_create_route_offsets_cumulative(self):
        """Test that time offsets are cumulative."""
        route = graph.create_route("test_route", ["M1", "M2", "M3", "M4"], [0, 2, 3, 1])
        assert route.time_offsets == [0, 2, 5, 6]


class TestRouteDefinitions:
    """Tests for route definitions."""

    def test_red_routes_exist(self):
        """Test red routes are defined."""
        assert graph.red_M1_M5 is not None
        assert graph.red_M2_M5 is not None
        assert graph.red_M5_M1 is not None
        assert graph.red_M5_M2 is not None

    def test_green_routes_exist(self):
        """Test green routes are defined."""
        assert graph.green_M1_M5 is not None
        assert graph.green_M2_M5 is not None
        assert graph.green_M5_M1 is not None
        assert graph.green_M5_M2 is not None

    def test_nanda_routes_exist(self):
        """Test Nanda routes are defined."""
        assert graph.nanda_M1_S1_r1 is not None
        assert graph.nanda_M1_S1_r2 is not None
        assert graph.nanda_S1_M1_r1 is not None
        assert graph.nanda_S1_M1_r2 is not None


class TestRouteResolver:
    """Tests for RouteResolver."""

    def test_resolve_main_campus_red_uphill(self):
        """Test resolving red line uphill route."""
        route = graph.RouteResolver.resolve_main_campus_route("red", "校門")
        assert route == graph.red_M1_M5

    def test_resolve_main_campus_red_downhill(self):
        """Test resolving red line downhill route."""
        route = graph.RouteResolver.resolve_main_campus_route("red", "台積館")
        assert route == graph.red_M5_M1

    def test_resolve_main_campus_red_downhill_from_gen2(self):
        """Test resolving red line downhill route ending at Gen2."""
        route = graph.RouteResolver.resolve_main_campus_route(
            "red", "台積館", is_from_gen2=True
        )
        assert route == graph.red_M5_M2

    def test_resolve_main_campus_red_from_gen2(self):
        """Test resolving red line from Gen2."""
        route = graph.RouteResolver.resolve_main_campus_route("red", "綜二")
        assert route == graph.red_M2_M5

    def test_resolve_main_campus_green_uphill(self):
        """Test resolving green line uphill route."""
        route = graph.RouteResolver.resolve_main_campus_route("green", "北校門")
        assert route == graph.green_M1_M5

    def test_resolve_main_campus_green_downhill(self):
        """Test resolving green line downhill route."""
        route = graph.RouteResolver.resolve_main_campus_route("green", "台積")
        assert route == graph.green_M5_M1

    def test_resolve_main_campus_green_from_gen2(self):
        """Test resolving green line from Gen2."""
        route = graph.RouteResolver.resolve_main_campus_route("green", "綜二")
        assert route == graph.green_M2_M5

    def test_resolve_main_campus_unknown_stop(self):
        """Test resolving unknown stop returns None."""
        route = graph.RouteResolver.resolve_main_campus_route("red", "未知站")
        assert route is None

    def test_resolve_nanda_route_up_route1(self):
        """Test resolving Nanda uphill route 1."""
        route = graph.RouteResolver.resolve_nanda_route("up", "一般路線")
        assert route == graph.nanda_M1_S1_r1

    def test_resolve_nanda_route_up_route2(self):
        """Test resolving Nanda uphill route 2."""
        route = graph.RouteResolver.resolve_nanda_route("up", "路線二經過教育學院")
        assert route == graph.nanda_M1_S1_r2

    def test_resolve_nanda_route_down_route1(self):
        """Test resolving Nanda downhill route 1."""
        route = graph.RouteResolver.resolve_nanda_route("down", "")
        assert route == graph.nanda_S1_M1_r1

    def test_resolve_nanda_route_down_route2(self):
        """Test resolving Nanda downhill route 2."""
        route = graph.RouteResolver.resolve_nanda_route("down", "教育學院")
        assert route == graph.nanda_S1_M1_r2

    def test_get_nanda_line_route1(self):
        """Test get_nanda_line returns route_1 for regular description."""
        line = graph.RouteResolver.get_nanda_line("一般路線")
        assert line == "route_1"

    def test_get_nanda_line_route2(self):
        """Test get_nanda_line returns route_2 for route 2 description."""
        line = graph.RouteResolver.get_nanda_line("路線二")
        assert line == "route_2"

    def test_get_nanda_line_education_building(self):
        """Test get_nanda_line returns route_2 for education building."""
        line = graph.RouteResolver.get_nanda_line("經過教育學院")
        assert line == "route_2"

    def test_get_nanda_line_none(self):
        """Test get_nanda_line handles None description."""
        line = graph.RouteResolver.get_nanda_line(None)
        assert line == "route_1"


class TestModels:
    """Tests for bus models."""

    def test_stop_model(self):
        """Test Stop model."""
        stop = models.Stop("T1", "測試站", "Test Stop", "24.0", "120.0")
        assert stop.id == "T1"
        assert stop.name == "測試站"
        assert stop.name_en == "Test Stop"

    def test_route_model(self):
        """Test Route model."""
        stop = models.Stop("T1", "測試站", "Test Stop", "24.0", "120.0")
        route = models.Route("test_route", [stop], [0])
        assert route.id == "test_route"
        assert len(route.stops) == 1
        assert route.time_offsets == [0]

    def test_bus_schedule_model(self):
        """Test BusSchedule model."""
        schedule = models.BusSchedule(
            time="08:00",
            description="往台積",
            bus_type="main",
            line="red",
            dep_stop="校門",
        )
        assert schedule.time == "08:00"
        assert schedule.bus_type == "main"

    def test_bus_detailed_schedule_model(self):
        """Test BusDetailedSchedule model."""
        schedule = models.BusDetailedSchedule(
            dep_info={"time": "08:00", "description": "往台積"},
            arr_info=[{"stop": "綜二", "arrive_time": "08:01"}],
            bus_type="main",
        )
        assert schedule.dep_info["time"] == "08:00"
        assert len(schedule.arr_info) == 1
