"""Shared campus-search service behavior after retiring departments REST routes."""

import pytest

from data_api.data.manager import nthudata
from data_api.domain.departments.services import departments_service


@pytest.mark.parametrize("metadata", [{}, {"title": None}, {"title": ""}])
async def test_search_handles_missing_optional_person_title(monkeypatch, metadata):
    async def get_directory(endpoint):
        return "test", [
            {"name": "Directory", "details": {"people": [{"name": "Alice", **metadata}]}}
        ]

    monkeypatch.setattr(nthudata, "get", get_directory)
    commit, result = await departments_service.fuzzy_search_departments_and_people("ZZZ")
    assert commit == "test"
    assert result == {"departments": [], "people": []}
