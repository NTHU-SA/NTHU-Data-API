from fastapi.testclient import TestClient

from src import app

client = TestClient(app)


def test_energy():
    response = client.get(url="/energy/electricity_usage")
    assert response.status_code == 200
