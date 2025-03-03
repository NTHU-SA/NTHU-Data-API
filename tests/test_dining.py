import pytest
from fastapi.testclient import TestClient

from src import app
from src.api import schemas

client = TestClient(app)
restaurant_name_list = ["麥當勞", "7-ELEVEN", "全家便利商店", "路易莎", "清華水漾"]


def test_dining_endpoints():
    response = client.get(url="/dining/")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "building_name", [_.value for _ in schemas.dining.DiningBuildingName]
)
def test_dining_buildings(building_name):
    response = client.get(url=f"/dining/buildings/{building_name}")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "day_of_week", [_.value for _ in schemas.dining.DiningScheduleName]
)
def test_dining_schedules(day_of_week):
    response = client.get(url=f"/dining/schedules/{day_of_week}")
    assert response.status_code == 200


@pytest.mark.parametrize("restaurant_name", restaurant_name_list)
def test_dining_searches_restaurants(restaurant_name):
    search_param = {"restaurant_name": restaurant_name}
    response = client.get(url="/dining/search", params=search_param)
    assert response.status_code == 200
