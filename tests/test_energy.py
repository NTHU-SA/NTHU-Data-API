from fastapi.testclient import TestClient

from data_api.api.api import app

client = TestClient(app)


def test_energy():
    response = client.get(url="/energy/electricity_usage")
    assert response.status_code == 200
