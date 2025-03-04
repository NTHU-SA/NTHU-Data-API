import pytest
from fastapi.testclient import TestClient

from src import app
from src.api import schemas

client = TestClient(app)


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/libraries/space", 200),
        ("/libraries/lost_and_found", 200),
        ("/libraries/goods", 200),
    ],
)
def test_libraries_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code


@pytest.mark.parametrize("rss", [_.value for _ in schemas.libraries.LibraryRssType])
def test_libraries_rss(rss):
    response = client.get(url=f"/libraries/rss/{rss}")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "library_name", [_.value for _ in schemas.libraries.LibraryName]
)
def test_libraries_openinghours(library_name):
    response = client.get(url=f"/libraries/openinghours/{library_name}")
    assert response.status_code == 200
