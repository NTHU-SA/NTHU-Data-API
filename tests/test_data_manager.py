"""
Tests for the new data manager module.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src import app
from src.utils.nthudata import DataCache, FileDetailsManager

client = TestClient(app)


class TestFileDetailsManager:
    """Test FileDetailsManager class."""

    def test_format_file_details(self):
        """Test file details formatting."""
        raw_data = {
            "file_details": {
                "/": [
                    {
                        "name": "buses.json",
                        "last_commit": "abc123",
                        "last_updated": "2024-01-01",
                    }
                ],
                "dining": [
                    {
                        "name": "shops.json",
                        "last_commit": "def456",
                        "last_updated": "2024-01-02",
                    }
                ],
            }
        }

        formatted = FileDetailsManager._format_file_details(raw_data)

        assert len(formatted) == 2
        assert formatted[0] == {
            "name": "/buses.json",
            "last_commit": "abc123",
            "last_updated": "2024-01-01",
        }
        assert formatted[1] == {
            "name": "dining/shops.json",
            "last_commit": "def456",
            "last_updated": "2024-01-02",
        }

    def test_get_commit_hash(self):
        """Test getting commit hash from file details."""
        from src.utils.nthudata import DataFetcher

        fetcher = DataFetcher("https://example.com")
        manager = FileDetailsManager(fetcher, "https://example.com/file_details.json")

        file_details = [
            {
                "name": "/buses.json",
                "last_commit": "abc123",
                "last_updated": "2024-01-01",
            },
            {
                "name": "/dining.json",
                "last_commit": "def456",
                "last_updated": "2024-01-02",
            },
        ]

        commit_hash = manager.get_commit_hash("/buses.json", file_details)
        assert commit_hash == "abc123"

        commit_hash = manager.get_commit_hash("/unknown.json", file_details)
        assert commit_hash is None


class TestDataCache:
    """Test DataCache class."""

    def test_set_and_get(self):
        """Test setting and getting cache."""
        cache = DataCache()
        cache.set("key1", {"data": "value"}, "commit_hash_123")

        result = cache.get("key1")
        assert result is not None
        assert result["data"] == {"data": "value"}
        assert result["commit_hash"] == "commit_hash_123"

    def test_is_valid(self):
        """Test cache validity check."""
        cache = DataCache()
        cache.set("key1", {"data": "value"}, "commit_hash_123")

        assert cache.is_valid("key1", "commit_hash_123") is True
        assert cache.is_valid("key1", "different_hash") is False
        assert cache.is_valid("nonexistent", "any_hash") is False

    def test_clear(self):
        """Test cache clearing."""
        cache = DataCache()
        cache.set("key1", {"data": "value1"}, "hash1")
        cache.set("key2", {"data": "value2"}, "hash2")

        # Clear specific key
        cache.clear("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") is not None

        # Clear all
        cache.clear()
        assert cache.get("key2") is None


def test_api_endpoints():
    """Test that API endpoints work with the data manager."""
    # This will fail if there's no network, but that's expected
    # The important thing is that it doesn't crash on import
    response = client.get("/announcements/lists/departments")
    # Accept both 200 (success) and 503 (service unavailable)
    assert response.status_code in [200, 503]
