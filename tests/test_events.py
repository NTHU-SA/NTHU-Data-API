import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/events/goodjob", 200),
        ("/events/arts_center", 200),
        ("/events/global_affairs", 200),
        ("/events/health_center", 200),
    ],
)
def test_events_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code
