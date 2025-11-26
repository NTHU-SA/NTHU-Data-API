"""Tests for the data manager module."""

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api.api import app
from data_api.data.nthudata import DataCache, DataFetcher, FileDetailsManager


class TestFileDetailsManager:
    """Tests for FileDetailsManager class."""

    async def test_format_file_details(self):
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

    async def test_get_commit_hash(self):
        """Test getting commit hash from file details."""
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
    """Tests for DataCache class."""

    async def test_set_and_get(self):
        """Test setting and getting cache."""
        cache = DataCache()
        cache.set("key1", {"data": "value"}, "commit_hash_123")

        result = cache.get("key1")
        assert result is not None
        assert result["data"] == {"data": "value"}
        assert result["commit_hash"] == "commit_hash_123"

    async def test_is_valid(self):
        """Test cache validity check."""
        cache = DataCache()
        cache.set("key1", {"data": "value"}, "commit_hash_123")

        assert cache.is_valid("key1", "commit_hash_123") is True
        assert cache.is_valid("key1", "different_hash") is False
        assert cache.is_valid("nonexistent", "any_hash") is False

    async def test_clear_specific_key(self):
        """Test clearing a specific cache key."""
        cache = DataCache()
        cache.set("key1", {"data": "value1"}, "hash1")
        cache.set("key2", {"data": "value2"}, "hash2")

        cache.clear("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") is not None

    async def test_clear_all_keys(self):
        """Test clearing all cache keys."""
        cache = DataCache()
        cache.set("key1", {"data": "value1"}, "hash1")
        cache.set("key2", {"data": "value2"}, "hash2")

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestDataManagerIntegration:
    """Integration tests for data manager with API endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_api_endpoints_with_data_manager(self, client: AsyncClient):
        """Test that API endpoints work with the data manager."""
        response = await client.get("/announcements/lists/departments")
        # Accept both 200 (success) and 503 (service unavailable)
        assert response.status_code in [200, 503]
