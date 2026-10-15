"""Shared directory-search service behavior."""

import pytest

from data_api.data.manager import nthudata
from data_api.domain.departments.services import departments_service


@pytest.mark.parametrize("metadata", [{}, {"title": None}, {"title": ""}])
@pytest.mark.parametrize("fuzzy", [True, False])
async def test_search_handles_missing_optional_person_title(monkeypatch, metadata, fuzzy):
    async def get_directory(endpoint):
        return "test", [
            {"name": "Directory", "details": {"people": [{"name": "Alice", **metadata}]}}
        ]

    monkeypatch.setattr(nthudata, "get", get_directory)
    commit, result = await departments_service.search_departments_and_people("ZZZ", fuzzy=fuzzy)
    assert commit == "test"
    assert result == {"departments": [], "people": []}
