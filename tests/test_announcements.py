import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)
department_list = ["清華公佈欄", "國立清華大學學生會"]


def test_announcements_endpoints():
    response = client.get(url="/announcements/")
    assert response.status_code == 200


def test_get_all_department():
    response = client.get(url="/announcements/departments")
    assert response.status_code == 200


@pytest.mark.parametrize("name", department_list)
def test_get_announcements_by_department(name):
    response = client.get(url=f"/announcements/departments/{name}")
    assert response.status_code == 200
