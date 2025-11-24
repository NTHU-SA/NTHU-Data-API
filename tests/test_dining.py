import pytest
from fastapi.testclient import TestClient

from data_api.api.api import app
from data_api.api import schemas

client = TestClient(app)
search_list = ["麥當勞", "7-ELEVEN", "全家便利商店", "路易莎", "清華水漾"]


def test_dining_endpoints():
    response = client.get(url="/dining")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "building_name", [_.value for _ in schemas.dining.DiningBuildingName]
)
def test_dining_buildings(building_name):
    params = {"building_name": building_name}
    response = client.get(url="/dining", params=params)
    assert response.status_code == 200


def test_dining_restaurants():
    response = client.get(url="/dining/restaurants")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "schedule", [_.value for _ in schemas.dining.DiningScheduleName]
)
def test_dining_schedules(schedule):
    params = {"schedule": schedule}
    response = client.get(url="/dining/restaurants", params=params)
    assert response.status_code == 200


@pytest.mark.parametrize("query", search_list)
def test_dining_searches_restaurants(query):
    params = {"query": query}
    response = client.get(url="/dining/search", params=params)
    assert response.status_code == 200
