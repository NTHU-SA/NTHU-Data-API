import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/resources/events/libarys", 200),
        ("/resources/events/goodjob", 200),
        ("/resources/events/arts_center", 200),
        ("/resources/events/global_affairs", 200),
        ("/resources/events/health_center", 200),
        ("/resources/events/bulletin/art_and_cultural", 200),
        ("/resources/events/bulletin/academic", 200),
        ("/resources/events/bulletin/academic", 200),
    ],
)
def test_events_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code
