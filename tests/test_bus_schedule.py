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
    assert (
        populated_buses.get_schedule(route_type=route, day=day, direction=direction, detailed=True)
        == full
    )


async def get_schedule(client, path="/buses/schedule", **params):
    route_parameter = "route" if path == "/buses/schedule" else "bus_type"
    return await client.get(
        path, params={route_parameter: "all", "day": "weekday", "direction": "all", **params}
    )


@pytest.mark.parametrize("details", [False, True])
async def test_rest_filters_before_limit_and_preserves_shape(populated_buses, details):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unfiltered = await get_schedule(client, details=details, limits=100)
        filtered = await get_schedule(
            client, details=details, stop=BusStopsName.M3.value, time="08:05", limits=1
        )
        legacy = await get_schedule(
            client,
            "/buses/schedules",
            details=details,
            stop=BusStopsName.M3.value,
            time="08:05",
            limits=1,
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


async def test_departure_filter_differs_from_legacy_arrival_filter(populated_buses):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, stop=BusStopsName.M5.value, time="08:01", limits=100)
        legacy = await get_schedule(
            client, f"/buses/stops/{BusStopsName.M5.value}", time="08:01", limits=100
        )
    assert response.status_code == legacy.status_code == 200
    assert all(bus["time"] >= "08:01" for bus in response.json())
    assert any(bus["dep_time"] == "08:00" for bus in legacy.json())
    assert all(bus["arrive_time"] >= "08:01" for bus in legacy.json())


@pytest.mark.parametrize("details", [False, True])
async def test_current_day_ignores_time(populated_buses, monkeypatch, details):
    monkeypatch.setattr(bus_router, "get_current_time_state", lambda: ("weekend", "08:50"))

    class FixedDatetime:
        @staticmethod
        def now():
            return datetime(2026, 10, 4, 8, 50)

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
        response = await get_schedule(client, details=details, limits=100)
        legacy = await get_schedule(client, "/buses/schedules", details=details, limits=100)
    assert response.status_code == legacy.status_code == 200
    assert response.json() == legacy.json()
    assert len(response.json()) == 5
    departures = [
        entry["dep_info"]["time"] if details else entry["time"] for entry in response.json()
    ]
    assert departures == ["08:00", "08:10", "08:15", "08:20", "08:30"]


@pytest.mark.parametrize(
    "params",
    [{"stop": "unknown"}, {"stop": ""}, {"limits": 0}, {"route": "unknown"}, {"route": ""}],
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
    new = paths["/buses/schedule"]["get"]
    assert not new.get("deprecated", False)
    assert new["operationId"] == "getBusSchedule"
    assert "stop" in {parameter["name"] for parameter in new["parameters"]}
    parameters = {parameter["name"]: parameter for parameter in new["parameters"]}
    assert "bus_type" not in parameters
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
        ({"stop": BusStopsName.M5.value}, ["08:10", "08:20", "08:30"]),
        ({"route": "main", "direction": "up"}, ["08:10", "08:20", "08:30"]),
        ({"route": "nanda"}, ["08:15"]),
        ({"time": "23:59"}, ["08:10", "08:15", "08:20", "08:30"]),
        ({"direction": "down"}, []),
        ({"limits": 2}, ["08:10", "08:15"]),
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
