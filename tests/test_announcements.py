"""Tests for announcements endpoints."""

from copy import deepcopy
from itertools import product

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.data.manager import nthudata
from data_api.domain.announcements.services import announcements_service

pytestmark = pytest.mark.usefixtures("dataset_runtime")


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

    async def test_get_announcements_sources(self, client: AsyncClient):
        """Test getting announcement sources."""
        response = await client.get("/announcements/sources")
        assert response.status_code == 200

    async def test_get_announcements_list_departments(self, client: AsyncClient):
        """Test listing announcement departments."""
        response = await client.get("/announcements/lists/departments")
        assert response.status_code == 200


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
