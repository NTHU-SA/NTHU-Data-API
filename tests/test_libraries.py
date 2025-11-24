import pytest
from fastapi.testclient import TestClient

from data_api.api.api import app
from data_api.api import schemas

client = TestClient(app)


# TODO: These endpoints need full migration from old libraries router
# @pytest.mark.parametrize(
#     "url, status_code",
#     [
#         ("/libraries/space", 200),
#         ("/libraries/lost_and_found", 200),
#         ("/libraries/goods", 200),
#     ],
# )
# def test_libraries_endpoints(url, status_code):
#     response = client.get(url=url)
#     assert response.status_code == status_code


# @pytest.mark.parametrize("rss", [_.value for _ in schemas.libraries.LibraryRssType])
# def test_libraries_rss(rss):
#     response = client.get(url=f"/libraries/rss/{rss}")
#     assert response.status_code == 200


@pytest.mark.parametrize(
    "library_name", [_.value for _ in schemas.libraries.LibraryName]
)
def test_libraries_search(library_name):
    response = client.get(url=f"/libraries/search?query={library_name}")
    assert response.status_code in [200, 503]  # 503 if no data available


def test_libraries_list():
    response = client.get(url="/libraries/")
    assert response.status_code in [200, 503]  # 503 if no data available
