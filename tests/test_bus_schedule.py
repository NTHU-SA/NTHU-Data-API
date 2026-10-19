"""Regression tests for unified bus schedules and stop filters."""

from datetime import datetime, timezone

import pytest
from fastmcp import Client
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.api.routers import buses as bus_router
from data_api.api.schemas.buses import BusCanonicalDetailedSchedule, BusCanonicalSchedule
from data_api.data.nthudata import NTHUDataManager, Snapshot
from data_api.domain.buses import services
from data_api.domain.buses.enums import BusStopsName
from data_api.mcp.server import mcp
from data_api.mcp.tools import buses as bus_tools
from data_api.runtime import default_runtime

pytestmark = pytest.mark.usefixtures("dataset_runtime")


def prepared_service(raw):
    manager = NTHUDataManager()
    service = services.BusesService(manager)
    now = datetime.now(timezone.utc)
    snapshot = Snapshot(raw, service.prepare(raw), "bus-fixture", now)
    service.state.snapshot = snapshot
    service.state.last_checked_at = now
    service.state.next_check = float("inf")
    service._snapshot = snapshot
    service.last_commit_hash = snapshot.version
    return service


@pytest.fixture
def populated_buses(monkeypatch):
    service = prepared_service(
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
    monkeypatch.setattr(services, "buses_service", service)
    monkeypatch.setattr(default_runtime, "buses", service)
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
        {
            **(bus if detailed else bus["dep_info"]),
            "arrive_time": next(
                arrival["arrive_time"]
                for arrival in bus["stops_time"]
                if arrival["stop"] == stop.value
            ),
        }
        for bus in full
        if any(arrival["stop"] == stop.value for arrival in bus["stops_time"])
    ]
    result = populated_buses.get_schedule(
        route_type=route, day=day, direction=direction, detailed=detailed, stop=stop
    )
    assert result == expected
    upcoming = [bus for bus in expected if bus["arrive_time"] >= "08:05"]
    assert (
        populated_buses.query_schedule(
            route_type=route,
            day=day,
            direction=direction,
            detailed=detailed,
            stop=stop,
            after_time="08:05",
            limit=1,
        )
        == upcoming[:1]
    )
    assert (
        populated_buses.get_schedule(route_type=route, day=day, direction=direction, detailed=True)
        == full
    )


async def get_schedule(client, path="/buses/schedule", **params):
    return await client.get(
        path, params={"route": "all", "day": "weekday", "direction": "all", **params}
    )


def canonical_schedules(schedules, details):
    model = BusCanonicalDetailedSchedule if details else BusCanonicalSchedule
    return [
        model.model_validate(bus).model_dump(mode="json", exclude_none=True) for bus in schedules
    ]


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


@pytest.mark.parametrize("path", ["/buses/schedule"])
@pytest.mark.parametrize("limit", [1, 2])
async def test_shared_limit_caps_bus_results(populated_buses, path, limit):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, path, limit=limit)
    assert response.status_code == 200
    assert len(response.json()) == limit


@pytest.mark.parametrize("path", ["/buses/schedule"])
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
    assert filtered.json() == canonical_schedules(expected, details)
    entry = filtered.json()[0]
    departure = entry["dep_info"] if details else entry
    assert departure["time"] == "08:10"
    assert "arrive_time" not in unfiltered.json()[0]
    assert set(entry) == {*unfiltered.json()[0], "arrive_time"}
    assert entry["arrive_time"] == "08:12"
    if details:
        assert "arrive_time" not in entry["dep_info"]
    assert filtered.headers["X-Data-Commit-Hash"] == "bus-fixture"
    if details:
        assert entry == BusCanonicalDetailedSchedule.model_validate(expected[0]).model_dump(
            mode="json", exclude_none=True
        )


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
async def test_stop_arrival_filter_matches_mcp(populated_buses, details, time, expected_times):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(
            client, stop=BusStopsName.M5.value, time=time, details=details, limit=100
        )
    assert response.status_code == 200
    departures = [bus["dep_info"] if details else bus for bus in response.json()]
    assert [bus["time"] for bus in departures] == expected_times
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
async def test_in_transit_bus_is_included_before_limit_for_selected_stop(populated_buses, details):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(
            client, stop=BusStopsName.M5.value, time="08:05", details=details, limit=1
        )
        no_stop = await get_schedule(client, time="08:05", details=details, limit=1)
    assert response.status_code == no_stop.status_code == 200
    departure = response.json()[0]["dep_info"] if details else response.json()[0]
    assert departure["time"] == "08:00"
    departure_without_stop = no_stop.json()[0]["dep_info"] if details else no_stop.json()[0]
    assert departure_without_stop["time"] == "08:10"
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
    assert data["buses"][0]["arrive_time"] == "08:12"
    if details:
        assert "arrive_time" not in data["buses"][0]["dep_info"]
    departure = data["buses"][0]["dep_info"] if details else data["buses"][0]
    assert departure["time"] == "08:10"
    assert departure["line"] == "main_green"
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
    assert response.status_code == 200
    assert len(response.json()) == 5
    departures = [
        entry["dep_info"]["time"] if details else entry["time"] for entry in response.json()
    ]
    assert departures == ["08:00", "08:10", "08:15", "08:20", "08:30"]
    lines = [entry["dep_info"]["line"] if details else entry["line"] for entry in response.json()]
    assert lines == ["main_red", "main_green", "nanda_route_2", "main_red", "main_green"]


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


def test_openapi_bus_parameters():
    paths = app.openapi()["paths"]
    bus_paths = {path for path in paths if path.startswith("/buses")}
    canonical_paths = {
        path for path in bus_paths if not paths[path]["get"].get("deprecated", False)
    }
    assert canonical_paths == {"/buses/routes", "/buses/stops", "/buses/schedule"}
    assert bus_paths == canonical_paths
    stops = paths["/buses/stops"]["get"]
    assert stops["operationId"] == "getBusStops"
    assert not stops.get("parameters")
    stop_schema = stops["responses"]["200"]["content"]["application/json"]["schema"]
    assert stop_schema["type"] == "array"
    assert stop_schema["items"] == {"$ref": "#/components/schemas/BusStopsInfo"}
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
    assert result.data["buses"] == canonical_schedules(expected, False)


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


@pytest.mark.parametrize(
    "line,expected",
    [
        ("red", "main_red"),
        ("green", "main_green"),
        ("route_1", "nanda_route_1"),
        ("route_2", "nanda_route_2"),
        ("main_red", "main_red"),
        ("main_green", "main_green"),
        ("nanda_route_1", "nanda_route_1"),
        ("nanda_route_2", "nanda_route_2"),
    ],
)
def test_canonical_line_identifiers(line, expected):
    bus = {
        "time": "11:30",
        "description": "",
        "dep_stop": "校門",
        "line": line,
        "bus_type": "large-sized_bus",
    }
    assert BusCanonicalSchedule.model_validate(bus).line == expected
    detailed = BusCanonicalDetailedSchedule.model_validate({"dep_info": bus, "stops_time": []})
    assert detailed.dep_info.line == expected
    assert bus["line"] == line


@pytest.mark.parametrize("details", [False, True])
async def test_published_nanda_line_rest_and_mcp(populated_buses, monkeypatch, details):
    published = {
        "weekdayBusScheduleTowardNanda": [{"time": "11:30", "description": "", "line": "route2"}],
        "weekdayBusScheduleTowardMainCampus": [
            {"time": "11:30", "description": "", "line": "route1"}
        ],
    }
    service = prepared_service(published)
    monkeypatch.setattr(services, "buses_service", service)
    monkeypatch.setattr(default_runtime, "buses", service)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await get_schedule(client, route="nanda", direction="up", details=details)
        education = await get_schedule(
            client, route="nanda", direction="up", stop=BusStopsName.M7.value, details=details
        )
        tsmc = await get_schedule(
            client, route="nanda", direction="up", stop=BusStopsName.M5.value, details=details
        )
        down = await get_schedule(client, route="nanda", direction="down", details=details)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_bus_schedule",
            {"route": "nanda", "day": "weekday", "direction": "up", "details": details},
        )
    assert response.status_code == education.status_code == 200
    assert down.status_code == tsmc.status_code == 200
    departure = response.json()[0]["dep_info"] if details else response.json()[0]
    assert departure == {
        "time": "11:30",
        "description": "",
        "dep_stop": "校門",
        "line": "nanda_route_2",
        "bus_type": "large-sized_bus",
    }
    assert education.json() == [{**response.json()[0], "arrive_time": "11:37"}]
    assert tsmc.json() == []
    down_departure = down.json()[0]["dep_info"] if details else down.json()[0]
    assert down_departure["line"] == "nanda_route_1"
    assert not result.is_error
    assert result.data["buses"] == response.json()
    if details:
        assert [arrival["stop"] for arrival in response.json()[0]["stops_time"]] == [
            BusStopsName.M1.value,
            BusStopsName.M2.value,
            BusStopsName.M6.value,
            BusStopsName.M7.value,
            BusStopsName.S1.value,
        ]
    assert service.get_schedule(
        route_type="nanda", day="weekday", direction="up", stop=BusStopsName.M7
    )
    assert (
        service.get_schedule(
            route_type="nanda", day="weekday", direction="up", stop=BusStopsName.M5
        )
        == []
    )
    assert published["weekdayBusScheduleTowardNanda"][0]["line"] == "route2"


@pytest.mark.parametrize("day", ["weekday", "weekend"])
@pytest.mark.parametrize("direction", ["up", "down"])
@pytest.mark.parametrize(
    "line,description,expected",
    [
        ("route1", "路線二", "route_1"),
        ("route2", "", "route_2"),
        ("route_1", "", "route_1"),
        ("route_2", "", "route_2"),
        ("nanda_route_1", "", "route_1"),
        ("nanda_route_2", "", "route_2"),
        ("", "路線二", "route_2"),
        ("", "", "route_1"),
    ],
)
def test_nanda_source_line_controls_schedule_and_stops(day, direction, line, description, expected):
    destination = "Nanda" if direction == "up" else "MainCampus"
    published = {
        f"{day}BusScheduleToward{destination}": [
            {"time": "11:30", "description": description, "line": line}
        ]
    }
    service = services.BusesService.prepare(published)
    result = service.query_schedule(route_type="nanda", day=day, direction=direction, detailed=True)
    assert result[0]["dep_info"]["line"] == expected
    stops = [arrival["stop"] for arrival in result[0]["stops_time"]]
    assert (BusStopsName.M7.value in stops) == (expected == "route_2")
    assert (BusStopsName.M5.value in stops) == (expected == "route_1")
    assert result[0]["stops_time"][0]["arrive_time"] == "11:30"
    assert published[f"{day}BusScheduleToward{destination}"][0]["line"] == line


def test_invalid_nanda_source_line_rejects_candidate():
    with pytest.raises(ValueError, match="Invalid Nanda bus line"):
        services.BusesService.prepare(
            {
                "weekdayBusScheduleTowardNanda": [
                    {"time": "11:30", "description": "", "line": "route3"}
                ]
            }
        )
