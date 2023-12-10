from fastapi.testclient import TestClient

from src import app

client = TestClient(app)


def test_careers():
    response = client.get(url="/resources/careers/bulletin/recruitment")
    assert response.status_code == 200
