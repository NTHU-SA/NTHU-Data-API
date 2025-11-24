import pytest
from fastapi.testclient import TestClient

from data_api.api import schemas
from data_api.api.api import app

client = TestClient(app)


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/libraries/space", 200),
        ("/libraries/lost_and_found", 200),
    ],
)
def test_libraries_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code


@pytest.mark.parametrize("rss", [_.value for _ in schemas.libraries.LibraryRssType])
def test_libraries_rss(rss):
    response = client.get(url=f"/libraries/rss/{rss}")
    assert response.status_code == 200
