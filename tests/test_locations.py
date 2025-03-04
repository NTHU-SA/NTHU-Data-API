import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)
search_list = ["校門", "綜合", "台積", "台達"]


def test_locations():
    response = client.get(url="/locations")
    assert response.status_code == 200


@pytest.mark.parametrize("query", search_list)
def test_locations_name(query):
    params = {"query": query}
    response = client.get(url="/locations/search", params=params)
    assert response.status_code == 200
