"""Tests for newsletters endpoints."""

from copy import deepcopy
from itertools import product

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app
from data_api.data.manager import nthudata
from data_api.domain.newsletters.services import newsletters_service

pytestmark = pytest.mark.usefixtures("dataset_runtime")


class TestNewslettersEndpoints:
    """Tests for newsletters endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_newsletters(self, client: AsyncClient):
        """Test getting all newsletters."""
        response = await client.get("/newsletters/")
        assert response.status_code == 200
        assert len(response.json()) == len(schemas.newsletters.NewsletterName)
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    async def test_get_sources(self, client: AsyncClient):
        response = await client.get("/newsletters/sources")
        assert response.status_code == 200
        assert len(response.json()) == len(schemas.newsletters.NewsletterName)
        assert all(set(source) == {"name", "link", "details"} for source in response.json())
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    @pytest.mark.parametrize(
        "newsletter_name",
        [_.value for _ in schemas.newsletters.NewsletterName],
    )
    async def test_get_newsletter_by_name(self, client: AsyncClient, newsletter_name: str):
        """Test getting newsletter by name."""
        response = await client.get(f"/newsletters/{newsletter_name}")
        assert response.status_code == 200
        replacement = await client.get(
            "/newsletters/", params={"name": newsletter_name, "fuzzy": False}
        )
        assert replacement.json() == [response.json()]

    async def test_legacy_missing_name(self, client: AsyncClient, monkeypatch):
        async def empty_dataset(endpoint):
            return "empty", []

        monkeypatch.setattr(nthudata, "get", empty_dataset)
        name = schemas.newsletters.NewsletterName.NTHU_Newsletter.value
        response = await client.get(f"/newsletters/{name}")
        assert response.status_code == 404
        assert response.json() == {"detail": "電子報名稱不存在"}


@pytest.fixture
def newsletter_data(monkeypatch):
    data = [
        {
            "name": "Alpha Newsletter",
            "link": "https://example.com/alpha",
            "details": {"publisher": "Alpha"},
            "articles": [
                {"title": "Notice", "date": "2026-10-01"},
                {"title": "XXXXXX"},
                {"title": None},
                {},
            ],
        },
        {
            "name": "ZZZZZZ",
            "link": "https://example.com/other",
            "details": {},
            "articles": [{"title": "Notice"}],
        },
        {
            "name": "Alpha Empty",
            "link": "https://example.com/empty",
            "details": {},
            "articles": [],
        },
    ]

    async def get_dataset(endpoint):
        assert endpoint == "newsletters.json"
        return "test", data

    monkeypatch.setattr(nthudata, "get", get_dataset)
    return data


@pytest.mark.parametrize("fuzzy,name_filter,title_filter", list(product([False, True], repeat=3)))
async def test_combined_filters_preserve_cached_data(
    newsletter_data, fuzzy, name_filter, title_filter
):
    original = deepcopy(newsletter_data)
    name = ("Alhpa" if fuzzy else "Alpha Newsletter") if name_filter else None
    title = ("Notise" if fuzzy else "Not") if title_filter else None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        params = {"fuzzy": fuzzy}
        if name:
            params["name"] = name
        if title:
            params["title"] = title
        response = await client.get("/newsletters/", params=params)
    assert response.status_code == 200
    expected = deepcopy(original)
    if name_filter:
        expected = [
            source
            for source in expected
            if (source["name"].startswith("Alpha") if fuzzy else source["name"] == name)
        ]
    if title_filter:
        expected = [
            {
                **source,
                "articles": [
                    article for article in source["articles"] if article.get("title") == "Notice"
                ],
            }
            for source in expected
            if any(article.get("title") == "Notice" for article in source["articles"])
        ]
    # REST supplies null defaults for optional article metadata.
    expected = [
        schemas.newsletters.NewsletterInfo.model_validate(source).model_dump(mode="json")
        for source in expected
    ]
    assert response.json() == expected
    assert response.headers["X-Data-Commit-Hash"] == "test"
    assert newsletter_data == original


@pytest.mark.parametrize(
    "path,params,expected_names",
    [
        ("/newsletters/", {"name": "Alpha Newsletter", "fuzzy": False}, ["Alpha Newsletter"]),
        ("/newsletters/", {"name": "Alpha", "fuzzy": False}, []),
        ("/newsletters/", {"title": "notice", "fuzzy": False}, []),
        ("/newsletters/", {"name": "Missing"}, []),
        ("/newsletters/", {"title": "Missing"}, []),
        ("/newsletters/", {"name": "", "title": ""}, ["Alpha Newsletter", "ZZZZZZ", "Alpha Empty"]),
        ("/newsletters/sources", {"name": "Alpha Newsletter"}, ["Alpha Newsletter"]),
        ("/newsletters/sources", {"name": "Alpha"}, []),
    ],
)
async def test_filter_edge_cases(newsletter_data, path, params, expected_names):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path, params=params)
    assert response.status_code == 200
    assert [source["name"] for source in response.json()] == expected_names
    if path.endswith("sources"):
        assert all("articles" not in source for source in response.json())


@pytest.mark.parametrize("score,matched", [(79, False), (80, True)])
@pytest.mark.parametrize("field", ["name", "title"])
async def test_fuzzy_threshold(newsletter_data, monkeypatch, score, matched, field):
    monkeypatch.setattr("thefuzz.fuzz.partial_ratio", lambda query, value: score)
    _, result = await newsletters_service.get_newsletters(**{field: "query"})
    assert bool(result) is matched


@pytest.mark.parametrize("path", ["/newsletters/", "/newsletters/sources"])
@pytest.mark.parametrize("dataset", [None, ("empty", []), (None, [])])
async def test_empty_and_unavailable_dataset(monkeypatch, path, dataset):
    async def get_dataset(endpoint):
        return dataset

    monkeypatch.setattr(nthudata, "get", get_dataset)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path)
    assert response.status_code == (503 if dataset is None else 200)
    if dataset is not None:
        assert response.json() == []
        assert response.headers.get("X-Data-Commit-Hash") == dataset[0]


def test_openapi_newsletter_contract():
    paths = app.openapi()["paths"]
    legacy = paths["/newsletters/{newsletter_name}"]["get"]
    assert legacy["deprecated"] is True
    assert legacy["operationId"] == "getNewsletterByName"
    query = paths["/newsletters"]["get"]
    assert query["operationId"] == "getAllNewsletters"
    parameters = {parameter["name"]: parameter for parameter in query["parameters"]}
    assert set(parameters) == {"name", "title", "fuzzy"}
    assert parameters["fuzzy"]["schema"]["default"] is True
    assert "deprecated" not in query
    assert paths["/newsletters/sources"]["get"]["operationId"] == "getNewsletterSources"
