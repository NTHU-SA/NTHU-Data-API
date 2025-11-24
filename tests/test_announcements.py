import pytest
from fastapi.testclient import TestClient

from data_api.api.api import app

client = TestClient(app)
department_list = ["清華公佈欄", "國立清華大學學生會"]


def test_announcements_endpoints():
    response = client.get(url="/announcements/")
    assert response.status_code == 200


@pytest.mark.parametrize("department", department_list)
def test_get_announcements_by_department(department):
    params = {"department": department}
    response = client.get(url="/announcements", params=params)
    assert response.status_code == 200


def test_search_announcements():
    params = {"query": "清華"}
    response = client.get(url="/announcements/search", params=params)
    assert response.status_code == 200
