"""Tests for utils module."""

from copy import deepcopy

import pytest

from data_api.utils.schema import url_corrector
from data_api.utils.search import fuzzy_matches


class TestUrlCorrector:
    """Tests for url_corrector function."""

    async def test_url_corrector_none_input(self):
        """Test that None input returns None."""
        result = url_corrector(None)
        assert result is None

    async def test_url_corrector_double_slash_prefix(self):
        """Test URL starting with //."""
        result = url_corrector("//example.com/path")
        assert result == "https://example.com/path"

    async def test_url_corrector_valid_http(self):
        """Test valid http URL is unchanged."""
        url = "http://example.com/path"
        result = url_corrector(url)
        assert result == url

    async def test_url_corrector_valid_https(self):
        """Test valid https URL is unchanged."""
        url = "https://example.com/path"
        result = url_corrector(url)
        assert result == url

    async def test_url_corrector_invalid_protocol(self):
        """Test URL with invalid protocol gets corrected."""
        result = url_corrector("ftp://example.com/path")
        assert result == "https://example.com/path"

    async def test_url_corrector_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = url_corrector("  https://example.com/path  ")
        assert result == "https://example.com/path"

    async def test_url_corrector_no_protocol(self):
        """Test URL without protocol is unchanged."""
        url = "example.com/path"
        result = url_corrector(url)
        assert result == url


@pytest.mark.parametrize("threshold", [60, 80])
def test_fuzzy_matches_rank_stably_without_mutating_input(monkeypatch, threshold):
    items = [
        {"title": "below"},
        {"title": "threshold"},
        {"title": "best", "id": 1},
        {"title": "best", "id": 2},
    ]
    original = deepcopy(items)
    scores = {"below": threshold - 1, "threshold": threshold, "best": 100}
    monkeypatch.setattr(
        "data_api.utils.search.fuzz.partial_ratio", lambda query, value: scores[value]
    )
    assert fuzzy_matches(items, "query", "title", threshold) == [items[2], items[3], items[1]]
    assert items == original
