import pytest
from fastapi.testclient import TestClient

from data_api.api import schemas
from data_api.api.api import app

client = TestClient(app)


@pytest.mark.parametrize("campus", ["main", "nanda"])
@pytest.mark.parametrize("direction", ["up", "down"])
def test_buses_endpoints(campus, direction):
    response = client.get(url=f"/buses/routes/?bus_type={campus}&direction={direction}")
    assert response.status_code == 200


def test_buses_stops_info():
    response = client.get(url="/buses/info/stops")
    assert response.status_code == 200


@pytest.mark.parametrize("bus_type", [_.value for _ in schemas.buses.BusRouteType])
@pytest.mark.parametrize("day", [_.value for _ in schemas.buses.BusDayWithCurrent])
@pytest.mark.parametrize("direction", [_.value for _ in schemas.buses.BusDirection])
def test_buses_schedules(bus_type, day, direction):
    response = client.get(
        url=f"/buses/schedules/?bus_type={bus_type}&day={day}&direction={direction}"
    )
    assert response.status_code == 200


@pytest.mark.parametrize("stop_name", [_.value for _ in schemas.buses.BusStopsName])
@pytest.mark.parametrize("bus_type", [_.value for _ in schemas.buses.BusRouteType])
@pytest.mark.parametrize("day", [_.value for _ in schemas.buses.BusDayWithCurrent])
@pytest.mark.parametrize("direction", [_.value for _ in schemas.buses.BusDirection])
@pytest.mark.parametrize("details", [True, False])
def test_buses_stops(stop_name, bus_type, day, direction, details):
    response = client.get(
        url=f"/buses/stops/{stop_name}/?bus_type={bus_type}&day={day}&direction={direction}&details={details}"
    )
    assert response.status_code == 200
