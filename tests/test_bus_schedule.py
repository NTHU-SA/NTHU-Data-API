"""Regression tests for unified bus schedules and stop filters."""

from datetime import datetime

import pytest
from fastmcp import Client
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.api.routers import buses as bus_router
from data_api.api.schemas.buses import BusDetailedSchedule
from data_api.domain.buses import services
from data_api.domain.buses.enums import BusStopsName
from data_api.mcp.server import mcp
from data_api.mcp.tools import buses as bus_tools

pytestmark = pytest.mark.usefixtures("dataset_runtime")


@pytest.fixture
def populated_buses(monkeypatch):
    service = services.BusesService.prepare(
        {
            "towardTSMCBuildingInfo": {
                "direction": "up",
                "duration": "2026",
                "route": "main-up",
                "routeEN": "Main up",
            },
            "towardMainGateInfo": {
                "direction": "down",
                "duration": "2026",
                "route": "main-down",
                "routeEN": "Main down",
            },
            "towardNandaInfo": {
                "direction": "up",
                "duration": "2026",
                "route": "nanda-up",
                "routeEN": "Nanda up",
            },
            "towardMainCampusInfo": {
                "direction": "down",
                "duration": "2026",
                "route": "nanda-down",
                "routeEN": "Nanda down",
            },
            "weekdayBusScheduleTowardTSMCBuilding": [
                {"time": "08:00", "description": "", "dep_stop": "校門", "line": "red"},
                {"time": "08:10", "description": "", "dep_stop": "校門", "line": "green"},
                {"time": "08:20", "description": "", "dep_stop": "校門", "line": "red"},
                {"time": "08:30", "description": "", "dep_stop": "校門", "line": "green"},
            ],
            "weekdayBusScheduleTowardNanda": [
                {"time": "08:15", "description": "路線二"},
            ],
            "weekendBusScheduleTowardTSMCBuilding": [
                {"time": "09:00", "description": "", "dep_stop": "校門", "line": "red"}
            ],
        }
    )
    service.last_commit_hash = "bus-fixture"

    async def update_data():
        pass

    monkeypatch.setattr(service, "update_data", update_data)
    monkeypatch.setattr(services, "buses_service", service)
    return service


@pytest.mark.parametrize("route", ["main", "nanda", "all"])
@pytest.mark.parametrize("day", ["weekday", "weekend"])
@pytest.mark.parametrize("direction", ["up", "down", "all"])
@pytest.mark.parametrize("stop", list(BusStopsName))
@pytest.mark.parametrize("detailed", [False, True])
def test_stop_filters_actual_route_membership(
    populated_buses, route, day, direction, stop, detailed
):
    full = populated_buses.get_schedule(
        route_type=route, day=day, direction=direction, detailed=True
    )
    expected = [
        bus for bus in full if any(arrival["stop"] == stop.value for arrival in bus["stops_time"])
    ]
    result = populated_buses.get_schedule(
        route_type=route, day=day, direction=direction, detailed=detailed, stop=stop
    )
    assert result == (expected if detailed else [bus["dep_info"] for bus in expected])
    upcoming = [
        bus
        for bus in expected
        if any(
            arrival["stop"] == stop.value and arrival["arrive_time"] >= "08:05"
            for arrival in bus["stops_time"]
        )
    ]
    assert populated_buses.query_schedule(
        route_type=route,
        day=day,
        direction=direction,
        detailed=detailed,
        stop=stop,
        after_time="08:05",
        limit=1,
    ) == (upcoming[:1] if detailed else [bus["dep_info"] for bus in upcoming[:1]])
    assert (
        populated_buses.get_schedule(route_type=route, day=day, direction=direction, detailed=True)
        == full
    )


async def get_schedule(client, path="/buses/schedule", **params):
    route_parameter = "route" if path == "/buses/schedule" else "bus_type"
    return await client.get(
        path, params={route_parameter: "all", "day": "weekday", "direction": "all", **params}
    )


@pytest.mark.parametrize("route", [None, "main", "nanda"])
@pytest.mark.parametrize("direction", [None, "up", "down"])
async def test_route_metadata_filters(populated_buses, route, direction):
    params = {}
    if route is not None:
        params["route"] = route
    if direction is not None:
        params["direction"] = direction
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/buses/routes", params=params)
    assert response.status_code == 200
    expected_routes = [
        f"{campus}-{bound}"
        for campus in ["main", "nanda"]
        for bound in ["up", "down"]
        if (route is None or route == campus) and (direction is None or direction == bound)
    ]
    assert [info["route"] for info in response.json()] == expected_routes
    assert response.headers["X-Data-Commit-Hash"] == "bus-fixture"


@pytest.mark.parametrize("route", ["unknown", "", "all"])
async def test_invalid_route_metadata_filter(populated_buses, route):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/buses/routes", params={"route": route})
    assert response.status_code == 422
    assert any(error["loc"] == ["query", "route"] for error in response.json()["detail"])


@pytest.mark.parametrize(
    "path", ["/buses/schedule", "/buses/schedules", f"/buses/stops/{BusStopsName.M5.value}"]
)
@pytest.mark.parametrize("limit", [1, 2])
async def test_shared_limit_caps_bus_results(populated_buses, path, limit):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, path, limit=limit)
    assert response.status_code == 200
    assert len(response.json()) == limit


@pytest.mark.parametrize(
    "path", ["/buses/schedule", "/buses/schedules", f"/buses/stops/{BusStopsName.M5.value}"]
)
@pytest.mark.parametrize("limit", [0, -1, "invalid"])
async def test_invalid_shared_limit_is_rejected(populated_buses, path, limit):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, path, limit=limit)
    assert response.status_code == 422
    assert any(error["loc"] == ["query", "limit"] for error in response.json()["detail"])


@pytest.mark.parametrize("details", [False, True])
async def test_rest_filters_before_limit_and_preserves_shape(populated_buses, details):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unfiltered = await get_schedule(client, details=details, limit=100)
        filtered = await get_schedule(
            client, details=details, stop=BusStopsName.M3.value, time="08:05", limit=1
        )
        legacy = await get_schedule(
            client,
            "/buses/schedules",
            details=details,
            stop=BusStopsName.M3.value,
            time="08:05",
            limit=1,
        )
    assert filtered.status_code == 200
    expected = populated_buses.query_schedule(
        route_type="all",
        day="weekday",
        direction="all",
        detailed=details,
        stop=BusStopsName.M3,
        after_time="08:05",
        limit=1,
    )
    assert len(expected) == 1
    assert filtered.json() == legacy.json()
    entry = filtered.json()[0]
    departure = entry["dep_info"] if details else entry
    assert departure["time"] == "08:10"
    assert set(entry) == set(unfiltered.json()[0])
    assert "arrive_time" not in entry
    assert filtered.headers["X-Data-Commit-Hash"] == "bus-fixture"
    if details:
        assert entry == BusDetailedSchedule.model_validate(expected[0]).model_dump(mode="json")


@pytest.mark.parametrize("details", [False, True])
@pytest.mark.parametrize(
    "time,expected_times",
    [
        ("08:05", ["08:00", "08:10", "08:20", "08:30"]),
        ("08:06", ["08:00", "08:10", "08:20", "08:30"]),
        ("08:07", ["08:10", "08:20", "08:30"]),
        ("08:16", ["08:10", "08:20", "08:30"]),
        ("08:37", []),
    ],
)
async def test_stop_arrival_filter_matches_legacy_stop_endpoint(
    populated_buses, details, time, expected_times
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(
            client, stop=BusStopsName.M5.value, time=time, details=details, limit=100
        )
        legacy = await get_schedule(
            client, f"/buses/stops/{BusStopsName.M5.value}", time=time, limit=100
        )
    assert response.status_code == legacy.status_code == 200
    departures = [bus["dep_info"] if details else bus for bus in response.json()]
    assert [bus["time"] for bus in departures] == expected_times
    assert [bus["dep_time"] for bus in legacy.json()] == expected_times
    assert all(bus["arrive_time"] >= time for bus in legacy.json())
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_bus_schedule",
            {
                "day": "weekday",
                "stop": BusStopsName.M5.value,
                "time": time,
                "details": details,
                "limit": 100,
            },
        )
    assert result.data["buses"] == response.json()


@pytest.mark.parametrize("details", [False, True])
async def test_in_transit_bus_is_included_before_limit_only_for_new_stop_query(
    populated_buses, details
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(
            client, stop=BusStopsName.M5.value, time="08:05", details=details, limit=1
        )
        legacy = await get_schedule(
            client,
            "/buses/schedules",
            stop=BusStopsName.M5.value,
            time="08:05",
            details=details,
            limit=1,
        )
        no_stop = await get_schedule(client, time="08:05", details=details, limit=1)
    assert response.status_code == legacy.status_code == no_stop.status_code == 200
    departure = response.json()[0]["dep_info"] if details else response.json()[0]
    assert departure["time"] == "08:00"
    legacy_departure = legacy.json()[0]["dep_info"] if details else legacy.json()[0]
    assert legacy_departure["time"] == "08:10"
    assert no_stop.json() == legacy.json()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_bus_schedule",
            {
                "day": "weekday",
                "stop": BusStopsName.M5.value,
                "time": "08:05",
                "details": details,
                "limit": 1,
            },
        )
    assert result.data["buses"] == response.json()


@pytest.mark.parametrize(
    "stop,time,expected_times",
    [
        (BusStopsName.M1, "08:01", ["08:10", "08:15", "08:20", "08:30"]),
        (BusStopsName.M3, "08:02", ["08:00", "08:10", "08:20", "08:30"]),
        (BusStopsName.M3, "08:05", ["08:10", "08:20", "08:30"]),
        (BusStopsName.S1, "08:30", ["08:15"]),
    ],
)
async def test_filter_uses_selected_stop_not_other_stops(
    populated_buses, stop, time, expected_times
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, stop=stop.value, time=time, limit=100)
    assert response.status_code == 200
    assert [bus["time"] for bus in response.json()] == expected_times


@pytest.mark.parametrize("details", [False, True])
async def test_current_day_ignores_time(populated_buses, monkeypatch, details):
    monkeypatch.setattr(bus_router, "get_current_time_state", lambda: ("weekend", "09:03"))

    class FixedDatetime:
        @staticmethod
        def now():
            return datetime(2026, 10, 4, 9, 3)

    monkeypatch.setattr(bus_tools, "datetime", FixedDatetime)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(
            client, day="current", stop=BusStopsName.M5.value, time="23:59", details=details
        )
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_bus_schedule",
            {"day": "current", "stop": BusStopsName.M5.value, "time": "23:59", "details": details},
        )
    assert response.status_code == 200
    assert len(response.json()) == 1
    departure = response.json()[0]["dep_info"] if details else response.json()[0]
    assert departure["time"] == "09:00"
    assert result.data["buses"] == response.json()


@pytest.mark.parametrize("details", [False, True])
async def test_mcp_stop_time_limit_and_metadata(populated_buses, details):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_bus_schedule",
            {
                "day": "weekday",
                "stop": BusStopsName.M3.value,
                "time": "08:05",
                "limit": 1,
                "details": details,
            },
        )
    data = result.data
    assert len(data["buses"]) == 1
    departure = data["buses"][0]["dep_info"] if details else data["buses"][0]
    assert departure["time"] == "08:10"
    assert data["stop_name"] == BusStopsName.M3.value
    assert len(data["stop_info"]) == 1
    assert {"latitude", "longitude"} <= data["stop_info"][0].keys()


async def test_no_matching_stop_returns_empty(populated_buses):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, route="main", stop=BusStopsName.S1.value)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("details", [False, True])
async def test_without_stop_preserves_existing_schedule(populated_buses, details):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, details=details, limit=100)
        legacy = await get_schedule(client, "/buses/schedules", details=details, limit=100)
    assert response.status_code == legacy.status_code == 200
    assert response.json() == legacy.json()
    assert len(response.json()) == 5
    departures = [
        entry["dep_info"]["time"] if details else entry["time"] for entry in response.json()
    ]
    assert departures == ["08:00", "08:10", "08:15", "08:20", "08:30"]


@pytest.mark.parametrize(
    "params",
    [{"stop": "unknown"}, {"stop": ""}, {"limit": 0}, {"route": "unknown"}, {"route": ""}],
)
async def test_invalid_rest_filters_are_rejected(populated_buses, params):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, **params)
    assert response.status_code == 422


@pytest.mark.parametrize("params", [{"stop": "unknown"}, {"stop": ""}, {"limit": 0}])
async def test_invalid_mcp_filters_are_rejected(populated_buses, params):
    async with Client(mcp) as client:
        result = await client.call_tool("get_bus_schedule", params, raise_on_error=False)
    assert result.is_error


def test_openapi_deprecation_and_stop_parameter():
    paths = app.openapi()["paths"]
    bus_paths = {path for path in paths if path.startswith("/buses")}
    canonical_paths = {
        path for path in bus_paths if not paths[path]["get"].get("deprecated", False)
    }
    assert canonical_paths == {"/buses/routes", "/buses/stops", "/buses/schedule"}
    assert bus_paths - canonical_paths == {
        "/buses/info/stops",
        "/buses/schedules",
        "/buses/stops/{stop_name}",
    }
    stops = paths["/buses/stops"]["get"]
    assert stops["operationId"] == "getBusStops"
    assert not stops.get("parameters")
    stop_schema = stops["responses"]["200"]["content"]["application/json"]["schema"]
    assert stop_schema["type"] == "array"
    assert stop_schema["items"] == {"$ref": "#/components/schemas/BusStopsInfo"}
    legacy_stops = paths["/buses/info/stops"]["get"]
    assert legacy_stops["deprecated"]
    assert legacy_stops["operationId"] == "getBusStopsInformation"
    assert "/buses/stops" in legacy_stops["description"]
    assert "下一個 major 版本移除" in legacy_stops["description"]
    assert not legacy_stops.get("parameters")
    assert legacy_stops["responses"]["200"]["content"]["application/json"]["schema"]["items"] == (
        stop_schema["items"]
    )
    new = paths["/buses/schedule"]["get"]
    assert not new.get("deprecated", False)
    assert new["operationId"] == "getBusSchedule"
    assert "stop" in {parameter["name"] for parameter in new["parameters"]}
    parameters = {parameter["name"]: parameter for parameter in new["parameters"]}
    assert "預估到站時間篩選" in parameters["stop"]["description"]
    assert set(parameters) == {"route", "direction", "day", "time", "stop", "limit", "details"}
    assert not parameters["limit"]["required"]
    assert parameters["limit"]["schema"]["default"] == 5
    assert {"type": "integer", "minimum": 1} in parameters["limit"]["schema"]["anyOf"]
    route_parameters = {
        parameter["name"]: parameter for parameter in paths["/buses/routes"]["get"]["parameters"]
    }
    assert set(route_parameters) == {"route", "direction"}
    assert not route_parameters["route"]["required"]
    assert route_parameters["route"]["schema"]["enum"] == ["main", "nanda"]
    for name, default in [("route", "all"), ("day", "current"), ("direction", "all")]:
        assert not parameters[name]["required"]
        assert parameters[name]["schema"]["default"] == default
    legacy_parameters = {
        parameter["name"]: parameter for parameter in paths["/buses/schedules"]["get"]["parameters"]
    }
    assert "route" not in legacy_parameters
    assert all(legacy_parameters[name]["required"] for name in ["bus_type", "day", "direction"])
    for path in ["/buses/schedules", "/buses/stops/{stop_name}"]:
        legacy = paths[path]["get"]
        assert legacy["deprecated"]
        assert "/buses/schedule" in legacy["description"]
        assert "下一個 major 版本移除" in legacy["description"]
        legacy_names = {parameter["name"] for parameter in legacy["parameters"]}
        assert "limit" in legacy_names
        assert "limits" not in legacy_names


@pytest.mark.parametrize("day", ["weekday", "weekend"])
@pytest.mark.parametrize(
    "time", ["25:00", "24:00", "08:60", "noon", "", "8:00", "08:0", " 08:00", "08:00\n"]
)
async def test_invalid_mcp_time_is_rejected_before_query(populated_buses, monkeypatch, day, time):
    def unexpected_query(**kwargs):
        pytest.fail("Invalid time must be rejected before querying schedules")

    monkeypatch.setattr(populated_buses, "query_schedule", unexpected_query)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_bus_schedule", {"day": day, "time": time}, raise_on_error=False
        )
    assert result.is_error


@pytest.mark.parametrize("day", ["weekday", "weekend"])
@pytest.mark.parametrize("time", ["00:00", "08:10", "23:59", None])
async def test_valid_mcp_time_filters(populated_buses, day, time):
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_bus_schedule", {"day": day, "time": time, "limit": 100, "details": False}
        )
    expected = populated_buses.query_schedule(
        route_type="all", day=day, direction="all", after_time=time or "", limit=100
    )
    assert result.data["buses"] == expected


@pytest.mark.parametrize(
    "params,expected_times",
    [
        ({}, ["08:10", "08:15", "08:20", "08:30"]),
        ({"stop": BusStopsName.M5.value}, ["08:00", "08:10", "08:20", "08:30"]),
        ({"route": "main", "direction": "up"}, ["08:10", "08:20", "08:30"]),
        ({"route": "nanda"}, ["08:15"]),
        ({"time": "23:59"}, ["08:10", "08:15", "08:20", "08:30"]),
        ({"direction": "down"}, []),
        ({"limit": 2}, ["08:10", "08:15"]),
    ],
)
async def test_canonical_defaults_query_upcoming_departures(
    populated_buses, monkeypatch, params, expected_times
):
    monkeypatch.setattr(bus_router, "get_current_time_state", lambda: ("weekday", "08:05"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/buses/schedule", params=params)
    assert response.status_code == 200
    assert [bus["time"] for bus in response.json()] == expected_times
    assert response.headers["X-Data-Commit-Hash"] == "bus-fixture"


async def test_canonical_default_limit(populated_buses, monkeypatch):
    monkeypatch.setattr(bus_router, "get_current_time_state", lambda: ("weekday", "00:00"))
    bus = populated_buses.raw_schedule_data[("all", "weekday", "all")][-1]
    populated_buses.raw_schedule_data[("all", "weekday", "all")].append({**bus, "time": "08:40"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/buses/schedule")
    assert response.status_code == 200
    assert [bus["time"] for bus in response.json()] == ["08:00", "08:10", "08:15", "08:20", "08:30"]


@pytest.mark.parametrize("path", ["/buses/schedules", "/buses/stops/台積館"])
@pytest.mark.parametrize("missing", ["bus_type", "day", "direction"])
async def test_legacy_query_parameters_remain_required(populated_buses, path, missing):
    params = {"bus_type": "main", "day": "weekday", "direction": "up"}
    del params[missing]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path, params=params)
    assert response.status_code == 422
    assert any(error["loc"] == ["query", missing] for error in response.json()["detail"])
