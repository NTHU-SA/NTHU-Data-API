import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)
id_list = [
    "b876aa09-40a8-427b-8bc7-1933978690e2",
    "6db26190-de4d-4d45-ae25-dccc5e47d795",
    "66e128f8-f457-489e-bbc4-b631ddc5edef",
]
name_list = ["校門", "產業", "綜合", "台積", "台達"]


def test_locations():
    response = client.get(url="/locations")
    assert response.status_code == 200


@pytest.mark.parametrize("id", id_list)
def test_locations_id(id):
    response = client.get(url=f"/locations/{id}")
    assert response.status_code == 200


@pytest.mark.parametrize("name", name_list)
def test_locations_name(name):
    response = client.get(url=f"/locations/searches/{name}")
    assert response.status_code == 200


@pytest.mark.parametrize("name", name_list)
def test_locations_searches(name):
    response = client.post(url="/locations/searches", json={"name": name})
    assert response.status_code == 200
