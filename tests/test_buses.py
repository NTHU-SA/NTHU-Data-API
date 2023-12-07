import pytest
from fastapi.testclient import TestClient

from src import app
from src.api import schemas

client = TestClient(app)


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/buses/main", 200),
        ("/buses/main/info/toward_main_gate", 200),
        ("/buses/main/info/toward_tsmc_building", 200),
        ("/buses/main/schedules/weekday/toward_main_gate", 200),
        ("/buses/main/schedules/weekday/toward_tsmc_building", 200),
        ("/buses/main/schedules/weekend/toward_main_gate", 200),
        ("/buses/main/schedules/weekend/toward_tsmc_building", 200),
        ("/buses/nanda", 200),
        ("/buses/nanda/info/toward_main_campus", 200),
        ("/buses/nanda/info/toward_south_campus", 200),
        ("/buses/nanda/schedules/weekday/toward_main_campus", 200),
        ("/buses/nanda/schedules/weekday/toward_south_campus", 200),
        ("/buses/nanda/schedules/weekend/toward_main_campus", 200),
        ("/buses/nanda/schedules/weekend/toward_south_campus", 200),
    ],
)
def test_buses_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code


@pytest.mark.parametrize("stop_name", [_.value for _ in schemas.buses.StopsName])
@pytest.mark.parametrize("bus_type", [_.value for _ in schemas.buses.BusType])
@pytest.mark.parametrize("day", [_.value for _ in schemas.buses.BusDay])
@pytest.mark.parametrize("direction", [_.value for _ in schemas.buses.BusDirection])
def test_buses_stops(stop_name, bus_type, day, direction):
    response = client.get(url=f"/buses/stops/{stop_name}/{bus_type}/{day}/{direction}")
    assert response.status_code == 200


@pytest.mark.parametrize("bus_type", [_.value for _ in schemas.buses.BusType])
@pytest.mark.parametrize("day", [_.value for _ in schemas.buses.BusDay])
@pytest.mark.parametrize("direction", [_.value for _ in schemas.buses.BusDirection])
def test_buses_detailed(bus_type, day, direction):
    response = client.get(url=f"/buses/detailed/{bus_type}/{day}/{direction}")
    assert response.status_code == 200
