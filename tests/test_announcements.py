"""Tests for announcements endpoints."""

from copy import deepcopy
from itertools import product

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.data.manager import nthudata
from data_api.domain.announcements.services import announcements_service

pytestmark = pytest.mark.usefixtures("dataset_runtime")


@pytest.fixture
def announcement_sources(monkeypatch):
    sources = [
        {
            "title": "Notice",
            "link": "https://academic.site.nthu.edu.tw/p/403-1007-1504-1.php",
            "department": "Academic",
            "language": "en",
            "articles": [
                {
                    "title": "Notice",
                    "link": "https://example.com/article",
                    "date": "2026-10-05",
                }
            ],
        },
        {
            "title": "Notice",
            "link": "http://academic.site.nthu.edu.tw/p/403-1007-1505-1.php",
            "department": "Academic",
            "language": "zh-tw",
            "articles": [],
        },
        {
            "title": "Notice",
            "link": "https://student.site.nthu.edu.tw/",
            "department": "Student",
            "language": "en",
            "articles": [
                {
                    "title": "Notice",
                    "link": "https://academic.site.nthu.edu.tw/article",
                    "date": "2026-10-05",
                }
            ],
        },
    ]
    original = deepcopy(sources)

    async def get_announcements(endpoint):
        assert endpoint == "announcements.json"
        return "test-commit", sources

    monkeypatch.setattr(nthudata, "get", get_announcements)
    yield sources
    assert sources == original


class TestAnnouncementsEndpoints:
    """Tests for announcements endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_announcements(self, client: AsyncClient):
        """Test getting all announcements."""
        response = await client.get("/announcements/")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "department",
        ["清華公佈欄", "國立清華大學學生會"],
    )
    async def test_get_announcements_by_department(self, client: AsyncClient, department: str):
        """Test getting announcements filtered by department."""
        params = {"department": department}
        response = await client.get("/announcements", params=params)
        assert response.status_code == 200

    @pytest.mark.parametrize("path", ["/announcements", "/announcements/"])
    @pytest.mark.parametrize("fuzzy", [False, True])
    @pytest.mark.parametrize(
        "url, indices",
        [
            ("academic.site.nthu.edu.tw", [0, 1]),
            ("academic.site.nthu.edu.tw/p/403-1007-1504-1.php", [0]),
            ("https://academic.site.nthu.edu.tw", [0, 1]),
            ("http://academic.site.nthu.edu.tw", [0, 1]),
            ("nonexistent.site.nthu.edu.tw", []),
            ("academic.site.nthu.edu.tx", []),
            ("", [0, 1, 2]),
        ],
    )
    async def test_filter_by_source_url(
        self, client: AsyncClient, announcement_sources, path, fuzzy, url, indices
    ):
        response = await client.get(path, params={"url": url, "fuzzy": fuzzy})
        assert response.status_code == 200
        expected = [announcement_sources[index] for index in indices]
        assert response.json() == expected
        assert response.headers["X-Data-Commit-Hash"] == "test-commit"

    @pytest.mark.parametrize("fuzzy", [False, True])
    async def test_url_combines_with_other_filters(
        self, client: AsyncClient, announcement_sources, fuzzy
    ):
        response = await client.get(
            "/announcements",
            params={
                "url": "academic.site.nthu.edu.tw",
                "department": "Academic",
                "title": "Notice",
                "language": "en",
                "fuzzy": fuzzy,
            },
        )
        assert response.status_code == 200
        assert response.json() == announcement_sources[:1]

    @pytest.mark.parametrize("department", [None, "教務處", "不存在的部門"])
    async def test_get_announcements_sources(self, client: AsyncClient, monkeypatch, department):
        """Test getting announcement sources."""
        sources = [
            {
                "title": "教務處公告",
                "link": "https://example.com/academic",
                "department": "教務處",
                "language": "zh-tw",
            },
            {
                "title": "學生事務處公告",
                "link": "https://example.com/student",
                "department": "學生事務處",
                "language": "zh-tw",
            },
        ]

        async def get_sources(endpoint):
            assert endpoint == "announcements_list.json"
            return "test-commit", sources

        monkeypatch.setattr(nthudata, "get", get_sources)
        params = {"department": department} if department else {}
        response = await client.get("/announcements/sources", params=params)
        assert response.status_code == 200
        expected = [
            source for source in sources if not department or source["department"] == department
        ]
        assert response.json() == expected
        assert response.headers["X-Data-Commit-Hash"] == "test-commit"

    @pytest.mark.parametrize(
        "sources, expected",
        [
            ([], []),
            (
                [
                    {"department": "Beta"},
                    {"department": "Alpha"},
                    {"department": "Beta"},
                ],
                ["Alpha", "Beta"],
            ),
        ],
    )
    async def test_deprecated_departments_endpoint(
        self, client: AsyncClient, monkeypatch, sources, expected
    ):
        """The deprecated endpoint preserves its sorted, unique response."""

        async def get_sources(endpoint):
            assert endpoint == "announcements_list.json"
            return "test-commit", sources

        monkeypatch.setattr(nthudata, "get", get_sources)
        response = await client.get("/announcements/lists/departments")
        assert response.status_code == 200
        assert response.json() == expected
        assert response.headers["X-Data-Commit-Hash"] == "test-commit"


def test_announcements_openapi_contract():
    schema = app.openapi()
    paths = schema["paths"]
    announcement_paths = {path for path in paths if path.startswith("/announcements")}
    assert announcement_paths == {
        "/announcements",
        "/announcements/",
        "/announcements/sources",
        "/announcements/lists/departments",
    }
    assert paths["/announcements"]["get"]["operationId"] == "getAnnouncements"
    assert paths["/announcements/sources"]["get"]["operationId"] == "getAnnouncementsList"
    assert not paths["/announcements"]["get"].get("deprecated", False)
    assert paths["/announcements/"]["get"]["deprecated"] is True
    assert not paths["/announcements/sources"]["get"].get("deprecated", False)
    legacy = paths["/announcements/lists/departments"]["get"]
    assert legacy["operationId"] == "listAnnouncementDepartments"
    assert legacy["deprecated"] is True
    assert "/announcements/sources" in legacy["description"]
    parameters = {
        parameter["name"]: parameter for parameter in paths["/announcements"]["get"]["parameters"]
    }
    assert {"department", "title", "language", "fuzzy", "url"} <= parameters.keys()
    assert parameters["url"]["required"] is False
    assert parameters["url"]["schema"]["type"] == "string"
    legacy_parameters = {
        parameter["name"] for parameter in paths["/announcements/"]["get"]["parameters"]
    }
    assert "url" in legacy_parameters
    description = parameters["department"]["description"]
    assert "/announcements/sources" in description
    assert "/announcements/lists/departments" not in description
    response_schema = paths["/announcements/sources"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert response_schema["type"] == "array"
    assert response_schema["items"] == {"$ref": "#/components/schemas/AnnouncementSource"}
    source_schema = schema["components"]["schemas"]["AnnouncementSource"]
    fields = {"title", "link", "language", "department"}
    assert set(source_schema["required"]) == fields
    assert set(source_schema["properties"]) == fields
    assert all(field["type"] == "string" for field in source_schema["properties"].values())
    assert source_schema["properties"]["link"]["format"] == "uri"


@pytest.mark.parametrize("selected", list(product([False, True], repeat=3)))
async def test_fuzzy_filters_preserve_sources_and_cached_articles(monkeypatch, selected):
    flags = list(product([False, True], repeat=3))
    data = [
        {
            "department": "Alpha" if department else "ZZZZZZ",
            "language": "en" if language else "zh-tw",
            "articles": [{"title": "Notice" if title else "XXXXXX"}],
        }
        for department, language, title in flags
    ]
    empty_source = {"department": "Alpha", "language": "en", "articles": []}
    data.append(empty_source)
    original = deepcopy(data)

    async def get_announcements(endpoint):
        return "test", data

    monkeypatch.setattr(nthudata, "get", get_announcements)
    department, language, title = selected
    commit, result = await announcements_service.fuzzy_search_announcements(
        department="Alpha" if department else None,
        language="en" if language else None,
        title="Notice" if title else None,
    )
    expected = [
        source
        for source, matches in zip(data, flags)
        if all(not enabled or matched for enabled, matched in zip(selected, matches))
    ]
    if not title:
        expected.append(empty_source)
    assert commit == "test"
    assert result == expected
    assert data == original
