import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/", 200),
        ("/ping", 200),
    ],
)
def test_default_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code
