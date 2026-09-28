"""Tests for buses endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app
from data_api.domain.buses.services import BusesService

pytestmark = pytest.mark.usefixtures("dataset_runtime")


def test_missing_route_metadata_is_not_registered():
    service = BusesService()
    service._res_json = {"towardMainCampusInfo": {"direction": "down"}}

    service._populate_info_data()

    assert service.get_route_info("nanda", "up") == []
    assert service.get_route_info("nanda", "down") == [{"direction": "down"}]


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
        self, client: AsyncClient, bus_type: str, day: str, direction: str
    ):
        """Test getting bus schedules by type, day and direction."""
        response = await client.get(
            f"/buses/schedules/?bus_type={bus_type}&day={day}&direction={direction}"
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
