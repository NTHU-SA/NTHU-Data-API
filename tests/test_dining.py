import pytest
from fastapi.testclient import TestClient

from src import app
from src.api import schemas

client = TestClient(app)
restaurant_name_list = ["麥當勞", "7-ELEVEN", "全家便利商店", "路易莎", "清華水漾"]


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/dining/", 200),
        ("/dining/buildings", 200),
        ("/dining/restaurants", 200),
    ],
)
def test_dining_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "building_name", [_.value for _ in schemas.dining.DiningBuildingName]
)
def test_dining_buildings(building_name):
    response = client.get(url=f"/dining/buildings/{building_name}")
    assert response.status_code == 200


@pytest.mark.parametrize("restaurant_name", restaurant_name_list)
def test_dining_restaurants(restaurant_name):
    response = client.get(url=f"/dining/restaurants/{restaurant_name}")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "day_of_week", [_.value for _ in schemas.dining.DiningSceduleName]
)
def test_dining_schedules(day_of_week):
    response = client.get(url=f"/dining/schedules/{day_of_week}")
    assert response.status_code == 200


@pytest.mark.parametrize("restaurant_name", restaurant_name_list)
def test_dining_searches_restaurants(restaurant_name):
    response = client.get(url=f"/dining/searches/restaurants/{restaurant_name}")
    assert response.status_code == 200
