import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)
search_list = ["校長", "高為元", "總務處"]


@pytest.mark.parametrize(
    "url, status_code",
    [
        ("/departments/", 200),
        ("/departments/01", 200),
    ],
)
def test_departments_endpoints(url, status_code):
    response = client.get(url=url)
    assert response.status_code == status_code


@pytest.mark.parametrize("name", search_list)
def test_departments_search(name):
    params = {"name": name}
    response = client.get(url="/departments/search/", params=params)
    assert response.status_code == 200
