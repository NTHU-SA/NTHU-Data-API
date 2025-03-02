import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)
name_list = ["校門", "綜合", "台積", "台達"]


def test_locations():
    response = client.get(url="/locations")
    assert response.status_code == 200


@pytest.mark.parametrize("name", name_list)
def test_locations_name(name):
    param = {"name": name}
    response = client.get(url="/locations/searches", params=param)
    assert response.status_code == 200
