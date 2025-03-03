import pytest
from fastapi.testclient import TestClient

from src import app
from src.api import schemas

client = TestClient(app)


@pytest.mark.parametrize("campus", ["main", "nanda"])
def test_buses_endpoints(campus):
    response = client.get(url=f"/buses/{campus}")
    assert response.status_code == 200


@pytest.mark.parametrize("bus_type", ["main", "nanda"])
@pytest.mark.parametrize("direction", ["up", "down"])
def test_buses_info(bus_type, direction):
    response = client.get(url=f"/buses/info/{bus_type}/{direction}")
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


@pytest.mark.parametrize("stop_name", [_.value for _ in schemas.buses.StopsName])
@pytest.mark.parametrize("bus_type", [_.value for _ in schemas.buses.BusRouteType])
@pytest.mark.parametrize("day", [_.value for _ in schemas.buses.BusDayWithCurrent])
@pytest.mark.parametrize("direction", [_.value for _ in schemas.buses.BusDirection])
def test_buses_stops(stop_name, bus_type, day, direction):
    response = client.get(
        url=f"/buses/stops/{stop_name}/?bus_type={bus_type}&day={day}&direction={direction}"
    )
    assert response.status_code == 200


@pytest.mark.parametrize("bus_type", [_.value for _ in schemas.buses.BusRouteType])
@pytest.mark.parametrize("day", [_.value for _ in schemas.buses.BusDayWithCurrent])
@pytest.mark.parametrize("direction", [_.value for _ in schemas.buses.BusDirection])
def test_buses_detailed(bus_type, day, direction):
    response = client.get(
        url=f"/buses/detailed?bus_type={bus_type}&day={day}&direction={direction}"
    )
    assert response.status_code == 200
