import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)
id_list = [
    "7e00db83-b407-4320-af55-0a1b1f5734ad",
    "8dfa4f30-2339-4ec2-aee9-0da58e78fdde",
    "ed3ac738-8102-43fb-844c-3abbd5f493d8",
    "4955571d-ec87-4c8f-bc39-c3b39142558c",
]
name_list = ["清華學院", "理學院", "主計"]


def test_phones():
    response = client.get(url="/phones")
    assert response.status_code == 200


@pytest.mark.parametrize("id", id_list)
def test_phones_id(id):
    response = client.get(url=f"/phones/{id}")
    assert response.status_code == 200


@pytest.mark.parametrize("name", name_list)
def test_phones_name(name):
    response = client.get(url=f"/phones/searches/{name}")
    assert response.status_code == 200


@pytest.mark.parametrize("name", name_list)
def test_phones_name_post(name):
    response = client.post(url="/phones/searches/", json={"name": name})
    assert response.status_code == 200
