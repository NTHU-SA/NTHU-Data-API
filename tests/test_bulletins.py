import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/bulletins/zh/行政公告", 200),
        ("/bulletins/zh/校內徵才", 200),
    ],
)
def test_events_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code
