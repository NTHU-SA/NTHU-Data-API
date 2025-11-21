"""
Tests for the new data manager module.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.nthudata import (
    DataCache,
    DataFetcher,
    FileDetailsManager,
    NTHUDataManager,
)


class TestDataFetcher:
    """Test DataFetcher class."""

    @pytest.mark.asyncio
    async def test_fetch_json_http_error(self):
        """Test JSON fetch with HTTP error."""
        fetcher = DataFetcher("https://example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = Exception("HTTP Error")

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.stream = AsyncMock()
            mock_client.stream.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_client.stream.return_value.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            result = await fetcher.fetch_json("https://example.com/data.json")
            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_json_invalid_json(self):
        """Test JSON fetch with invalid JSON."""
        fetcher = DataFetcher("https://example.com")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.aread = AsyncMock(return_value=b"invalid json")

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.stream = AsyncMock()
            mock_client.stream.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_client.stream.return_value.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            result = await fetcher.fetch_json("https://example.com/data.json")
            assert result is None


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


class TestNTHUDataManager:
    """Test NTHUDataManager class."""

    def test_normalize_endpoint_name(self):
        """Test endpoint name normalization."""
        manager = NTHUDataManager(base_url="https://example.com")

        # Test with base_url not ending with /
        assert manager._normalize_endpoint_name("buses.json") == "/buses.json"
        assert manager._normalize_endpoint_name("/buses.json") == "/buses.json"

        # Test with base_url ending with /
        manager.base_url = "https://example.com/"
        assert manager._normalize_endpoint_name("buses.json") == "buses.json"
        assert manager._normalize_endpoint_name("/buses.json") == "buses.json"

    @pytest.mark.asyncio
    async def test_get_with_valid_cache(self):
        """Test get with valid cache."""
        manager = NTHUDataManager(base_url="https://example.com")

        # Mock file details
        file_details = [
            {
                "name": "/buses.json",
                "last_commit": "abc123",
                "last_updated": "2024-01-01",
            }
        ]
        manager.file_details_manager.get_file_details = AsyncMock(
            return_value=file_details
        )

        # Set up cache with matching commit hash
        manager.cache.set("/buses.json", {"data": "cached_value"}, "abc123")

        result = await manager.get("buses.json")

        assert result is not None
        assert result[0] == "abc123"
        assert result[1] == {"data": "cached_value"}

    @pytest.mark.asyncio
    async def test_get_with_invalid_cache(self):
        """Test get with invalid cache (needs refresh)."""
        manager = NTHUDataManager(base_url="https://example.com")

        # Mock file details
        file_details = [
            {
                "name": "/buses.json",
                "last_commit": "new_hash",
                "last_updated": "2024-01-01",
            }
        ]
        manager.file_details_manager.get_file_details = AsyncMock(
            return_value=file_details
        )

        # Set up cache with different commit hash
        manager.cache.set("/buses.json", {"data": "old_value"}, "old_hash")

        # Mock fetcher to return new data
        manager.fetcher.fetch_json = AsyncMock(return_value={"data": "new_value"})

        result = await manager.get("buses.json")

        assert result is not None
        assert result[0] == "new_hash"
        assert result[1] == {"data": "new_value"}

    @pytest.mark.asyncio
    async def test_get_with_no_file_details(self):
        """Test get when file_details is unavailable."""
        manager = NTHUDataManager(base_url="https://example.com")

        # Mock file details to return None
        manager.file_details_manager.get_file_details = AsyncMock(return_value=None)

        result = await manager.get("buses.json")

        assert result is None

    @pytest.mark.asyncio
    async def test_prefetch(self):
        """Test prefetching multiple endpoints."""
        manager = NTHUDataManager(base_url="https://example.com")

        # Mock get method
        async def mock_get(endpoint):
            if endpoint == "buses.json":
                return ("hash1", {"data": "buses"})
            elif endpoint == "dining.json":
                return ("hash2", {"data": "dining"})
            else:
                return None

        manager.get = AsyncMock(side_effect=mock_get)

        results = await manager.prefetch(["buses.json", "dining.json", "unknown.json"])

        assert results["buses.json"] is True
        assert results["dining.json"] is True
        assert results["unknown.json"] is False
