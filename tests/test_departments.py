import pytest
from fastapi.testclient import TestClient

from data_api.api.api import app

client = TestClient(app)
search_list = ["校長", "高為元", "總務處"]


def test_departments_endpoints():
    response = client.get(url="/departments/")
    assert response.status_code == 200


def test_departments_index():
    response = client.get(url="/departments/01")
    assert response.status_code == 200


@pytest.mark.parametrize("query", search_list)
def test_departments_search(query):
    params = {"query": query}
    response = client.get(url="/departments/search/", params=params)
    assert response.status_code == 200
