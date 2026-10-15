"""Tests for newsletters endpoints."""

from copy import deepcopy
from itertools import product
from unittest.mock import AsyncMock

import pytest
from conftest import NEWSLETTER_NAMES
from fastmcp import Client
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app
from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.domain.newsletters.services import newsletters_service
from data_api.mcp.server import mcp
from data_api.mcp.tools.newsletters import _get_newsletters
from data_api.runtime import get_runtime

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
        response = await client.get("/newsletters")
        assert response.status_code == 200
        assert [source["name"] for source in response.json()] == NEWSLETTER_NAMES
        assert response.headers["X-Data-Commit-Hash"] == "fixture"

    async def test_get_sources(self, client: AsyncClient):
        response = await client.get("/newsletters/sources")
        assert response.status_code == 200
        assert [source["name"] for source in response.json()] == NEWSLETTER_NAMES
        assert all(set(source) == {"name", "link", "details"} for source in response.json())
        assert response.headers["X-Data-Commit-Hash"] == "fixture"


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
        response = await client.get("/newsletters", params=params)
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
        ("/newsletters", {"name": "Alpha Newsletter", "fuzzy": False}, ["Alpha Newsletter"]),
        ("/newsletters", {"name": "Alpha", "fuzzy": False}, []),
        ("/newsletters", {"title": "notice", "fuzzy": False}, []),
        ("/newsletters", {"name": "Missing"}, []),
        ("/newsletters", {"title": "Missing"}, []),
        ("/newsletters", {"name": "", "title": ""}, ["Alpha Newsletter", "ZZZZZZ", "Alpha Empty"]),
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


@pytest.mark.parametrize("score,matched", [(59, False), (60, True)])
@pytest.mark.parametrize("field", ["name", "title"])
async def test_fuzzy_threshold(newsletter_data, monkeypatch, score, matched, field):
    monkeypatch.setattr("thefuzz.fuzz.partial_ratio", lambda query, value: score)
    _, result = await newsletters_service.get_newsletters(**{field: "query"})
    assert bool(result) is matched


@pytest.mark.parametrize("search", [None, "", "Alhpa", "Missing"])
async def test_mcp_and_rest_name_search_match(newsletter_data, search):
    original = deepcopy(newsletter_data)
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as rest,
        Client(mcp) as tools,
    ):
        response = await rest.get("/newsletters", params={"name": search or ""})
        result = await tools.call_tool("get_newsletters", {"search": search})
    assert response.status_code == 200
    assert not result.is_error
    assert [source["name"] for source in result.data["newsletters"]] == [
        source["name"] for source in response.json()
    ]
    assert result.data["count"] == len(response.json())
    assert newsletter_data == original


@pytest.mark.parametrize("search", [None, "", "query"])
async def test_mcp_delegates_search_to_domain(monkeypatch, search):
    get_newsletters = AsyncMock(return_value=("test", []))
    monkeypatch.setattr(get_runtime().newsletters, "get_newsletters", get_newsletters)
    assert await _get_newsletters(search) == {"count": 0, "newsletters": []}
    get_newsletters.assert_awaited_once_with(name=search)


@pytest.mark.parametrize("score,matched", [(59, False), (60, True)])
async def test_rest_and_mcp_share_fuzzy_threshold(newsletter_data, monkeypatch, score, matched):
    monkeypatch.setattr("thefuzz.fuzz.partial_ratio", lambda query, value: score)
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as rest,
        Client(mcp) as tools,
    ):
        response = await rest.get("/newsletters", params={"name": "query"})
        result = await tools.call_tool("get_newsletters", {"search": "query"})
    assert response.status_code == 200
    assert not result.is_error
    expected_names = [source["name"] for source in newsletter_data] if matched else []
    assert [source["name"] for source in response.json()] == expected_names
    assert [source["name"] for source in result.data["newsletters"]] == expected_names
    assert result.data["count"] == len(expected_names)


@pytest.mark.parametrize("search", [None, "", "Alpha", "ZZZZZZ"])
async def test_mcp_returns_all_matching_sources(newsletter_data, search):
    template = deepcopy(newsletter_data[0])
    newsletter_data[:] = [
        {**deepcopy(template), "name": f"Alpha {index}"} for index in range(20)
    ] + [
        {**deepcopy(template), "name": "ZZZZZZ"},
        {**deepcopy(template), "name": "Alpha Empty", "articles": []},
    ]
    original = deepcopy(newsletter_data)
    if search == "Alpha":
        expected = original[:20] + original[-1:]
    elif search == "ZZZZZZ":
        expected = original[20:21]
    else:
        expected = original
    async with Client(mcp) as tools:
        result = await tools.call_tool("get_newsletters", {"search": search})
    assert not result.is_error
    assert result.data == {
        "count": len(expected),
        "newsletters": [
            {
                "name": source["name"],
                "link": source["link"],
                "latest_articles": [
                    {"title": article.get("title"), "date": article.get("date")}
                    for article in source["articles"][:3]
                ],
            }
            for source in expected
        ],
    }
    assert newsletter_data == original


@pytest.mark.parametrize("path", ["/newsletters", "/newsletters/sources"])
@pytest.mark.parametrize("dataset", [None, ("empty", []), (None, [])])
async def test_empty_and_unavailable_dataset(monkeypatch, path, dataset):
    async def get_dataset(endpoint):
        if dataset is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")
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
    query = paths["/newsletters"]["get"]
    assert query["operationId"] == "getAllNewsletters"
    parameters = {parameter["name"]: parameter for parameter in query["parameters"]}
    assert set(parameters) == {"name", "title", "fuzzy"}
    assert parameters["fuzzy"]["schema"]["default"] is True
    assert "deprecated" not in query
    assert paths["/newsletters/sources"]["get"]["operationId"] == "getNewsletterSources"
