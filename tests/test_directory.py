"""Tests for the unified directory endpoint."""

from copy import deepcopy

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.api.schemas.departments import Department
from data_api.data.manager import nthudata
from data_api.domain.departments import services

pytestmark = pytest.mark.usefixtures("dataset_runtime")


@pytest.fixture
def directory_data(monkeypatch):
    data = [
        {
            "index": "admin",
            "name": "校務處",
            "parent_name": "清華大學",
            "url": "https://example.com/admin",
            "details": {
                "contact": {"phone": "123"},
                "departments": [{"name": "行政組"}],
                "people": [
                    {"name": "王小明", "title": "主任", "extension": "100"},
                    {"name": "陳大華", "title": None},
                    {"name": "林美玲"},
                ],
            },
        },
        {
            "index": "computing",
            "name": "計算中心",
            "details": {
                "contact": {"email": "computing@example.com"},
                "people": [
                    {"name": "王小明", "title": ""},
                    {"name": "李大同", "title": "主任"},
                ],
            },
        },
        {"index": "library", "name": "圖書館"},
    ]

    async def get_directory(endpoint):
        assert endpoint == services.JSON_PATH
        return "directory-commit", data

    monkeypatch.setattr(nthudata, "get", get_directory)
    return data


@pytest.mark.parametrize(
    "query,indices,people",
    [
        (None, ["admin", "computing", "library"], None),
        ("", ["admin", "computing", "library"], None),
        ("校務處", ["admin"], None),
        ("圖書館", ["library"], None),
        ("王小明", ["admin", "computing"], [["王小明"], ["王小明"]]),
        ("主任", ["admin", "computing"], [["王小明"], ["李大同"]]),
        ("ZZZ", [], None),
    ],
)
async def test_directory_query(directory_data, query, indices, people):
    original = deepcopy(directory_data)
    expected = [deepcopy(item) for item in directory_data if item["index"] in indices]
    if people is not None:
        for department, names in zip(expected, people, strict=True):
            department["details"]["people"] = [
                person for person in department["details"]["people"] if person["name"] in names
            ]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as client:
        response = await client.get("/directory", params={} if query is None else {"query": query})
        unfiltered = await client.get("/directory")
        legacy = await client.get("/departments/")

    assert response.status_code == 200
    assert "location" not in response.headers
    assert response.headers["X-Data-Commit-Hash"] == "directory-commit"
    assert response.json() == [
        Department.model_validate(item).model_dump(mode="json") for item in expected
    ]
    assert unfiltered.json() == legacy.json()
    assert directory_data == original


async def test_directory_department_match_keeps_nonmatching_people(directory_data, monkeypatch):
    scores = {"校務處": 80, "計算中心": 79, "王小明": 80, "主任": 89}
    monkeypatch.setattr(services.fuzz, "partial_ratio", lambda query, value: scores.get(value, 0))
    commit, results = await services.departments_service.get_directory("query")
    assert commit == "directory-commit"
    assert results[0] == directory_data[0]
    assert results[1]["details"]["people"] == [directory_data[1]["details"]["people"][0]]


@pytest.mark.parametrize("score,expected_count", [(89, 0), (90, 2)])
async def test_directory_title_match_threshold(directory_data, monkeypatch, score, expected_count):
    monkeypatch.setattr(
        services.fuzz, "partial_ratio", lambda query, value: score if value == "主任" else 0
    )
    _, results = await services.departments_service.get_directory("query")
    assert len(results) == expected_count
    for department in results:
        assert len(department["details"]["people"]) == 1
        assert department["details"]["people"][0]["title"] == "主任"


async def test_directory_sorts_by_match_score(directory_data, monkeypatch):
    scores = {"校務處": 80, "計算中心": 100}
    monkeypatch.setattr(services.fuzz, "partial_ratio", lambda query, value: scores.get(value, 0))
    _, results = await services.departments_service.get_directory("query")
    assert [department["index"] for department in results] == ["computing", "admin"]


async def test_legacy_search_keeps_separate_results(directory_data):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/departments/search", params={"query": "王小明"})
    assert response.status_code == 200
    assert response.headers["X-Data-Commit-Hash"] == "directory-commit"
    assert response.json()["departments"] == []
    assert [person["name"] for person in response.json()["people"]] == ["王小明", "王小明"]


async def test_directory_without_commit_hash(monkeypatch):
    async def get_directory(endpoint):
        return None, []

    monkeypatch.setattr(nthudata, "get", get_directory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/directory")
    assert response.status_code == 200
    assert response.json() == []
    assert "X-Data-Commit-Hash" not in response.headers


def test_directory_openapi():
    schema = app.openapi()
    paths = schema["paths"]
    assert "/directory/search" not in paths
    operation = paths["/directory"]["get"]
    assert operation["tags"] == ["directory"]
    assert operation["operationId"] == "getDirectory"
    assert not operation.get("deprecated", False)
    assert operation["parameters"][0]["name"] == "query"
    assert operation["parameters"][0]["required"] is False
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["items"] == {
        "$ref": "#/components/schemas/Department"
    }


async def test_directory_search_path_is_not_registered():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/directory/search", params={"query": "test"})
    assert response.status_code == 404


@pytest.mark.parametrize("query", [None, "王小明"])
async def test_directory_unavailable_dataset(monkeypatch, query):
    async def unavailable(endpoint):
        return None

    monkeypatch.setattr(nthudata, "get", unavailable)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/directory", params={} if query is None else {"query": query})
    assert response.status_code == 503
    assert response.json() == {"detail": "Service temporarily unavailable"}
