"""Tests for buses endpoints."""

import pytest
from fastmcp import Client
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app
from data_api.domain.buses.services import BusesService, buses_service
from data_api.mcp.server import mcp

pytestmark = pytest.mark.usefixtures("dataset_runtime")


def test_missing_route_metadata_is_not_registered():
    service = BusesService()
    service._res_json = {"towardMainCampusInfo": {"direction": "down"}}

    service._populate_info_data()

    assert service.get_route_info("nanda", "up") == []
    assert service.get_route_info("nanda", "down") == [{"direction": "down"}]


@pytest.mark.parametrize(
    "path,method",
    [
        ("/buses/routes", "get_route_info"),
        ("/buses/info/stops", "gen_bus_stops_info"),
        (
            "/buses/schedules?bus_type=main&day=weekday&direction=up",
            "get_schedule",
        ),
        (
            "/buses/schedule?route=main&day=weekday&direction=up&stop=台積館",
            "get_schedule",
        ),
        (
            "/buses/stops/台積館?bus_type=main&day=weekday&direction=up",
            "get_stop_schedule",
        ),
    ],
)
async def test_internal_bus_errors_are_safe(monkeypatch, caplog, path, method):
    def fail(*args, **kwargs):
        raise RuntimeError("Private bus failure at https://upstream.example")

    monkeypatch.setattr(buses_service, method, fail)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.get(path, headers={"Origin": "https://example.com"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert float(response.headers["X-Process-Time"]) >= 0
    assert "Private bus failure" in caplog.text


async def test_unexpected_bus_tool_errors_are_masked(monkeypatch, caplog):
    async def fail():
        raise RuntimeError("Private bus failure at https://upstream.example")

    monkeypatch.setattr(buses_service, "update_data", fail)
    async with Client(mcp) as client:
        result = await client.call_tool("get_bus_schedule", {}, raise_on_error=False)
    assert result.is_error
    assert "Private" not in result.content[0].text
    assert "http" not in result.content[0].text
    assert "Private bus failure" in caplog.text


class TestBusesRoutes:
    """Tests for bus routes endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    @pytest.mark.parametrize("campus", ["main", "nanda"])
    @pytest.mark.parametrize("direction", ["up", "down"])
    async def test_get_bus_routes(self, client: AsyncClient, campus: str, direction: str):
        """Test getting bus routes by campus and direction."""
        response = await client.get(f"/buses/routes/?bus_type={campus}&direction={direction}")
        assert response.status_code == 200


class TestBusesInfo:
    """Tests for bus information endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_bus_stops_info(self, client: AsyncClient):
        """Test getting bus stops information."""
        response = await client.get("/buses/info/stops")
        assert response.status_code == 200


class TestBusesSchedules:
    """Tests for bus schedules endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    @pytest.mark.parametrize("path", ["/buses/schedule", "/buses/schedules"])
    @pytest.mark.parametrize(
        "bus_type",
        [_.value for _ in schemas.buses.BusRouteType],
    )
    @pytest.mark.parametrize(
        "day",
        [_.value for _ in schemas.buses.BusDayWithCurrent],
    )
    @pytest.mark.parametrize(
        "direction",
        [_.value for _ in schemas.buses.BusDirection],
    )
    async def test_get_bus_schedules(
        self, client: AsyncClient, bus_type: str, day: str, direction: str, path: str
    ):
        """Test getting bus schedules by type, day and direction."""
        route_parameter = "route" if path == "/buses/schedule" else "bus_type"
        response = await client.get(
            f"{path}?{route_parameter}={bus_type}&day={day}&direction={direction}"
        )
        assert response.status_code == 200


class TestBusesStops:
    """Tests for bus stops endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    @pytest.mark.parametrize(
        "stop_name",
        [_.value for _ in schemas.buses.BusStopsName],
    )
    @pytest.mark.parametrize(
        "bus_type",
        [_.value for _ in schemas.buses.BusRouteType],
    )
    @pytest.mark.parametrize(
        "day",
        [_.value for _ in schemas.buses.BusDayWithCurrent],
    )
    @pytest.mark.parametrize(
        "direction",
        [_.value for _ in schemas.buses.BusDirection],
    )
    @pytest.mark.parametrize("details", [True, False])
    async def test_get_bus_stop_arrivals(
        self,
        client: AsyncClient,
        stop_name: str,
        bus_type: str,
        day: str,
        direction: str,
        details: bool,
    ):
        """Test getting bus arrivals at a specific stop."""
        response = await client.get(
            f"/buses/stops/{stop_name}/?bus_type={bus_type}&day={day}&direction={direction}&details={details}"
        )
        assert response.status_code == 200
