"""
Data Manager for NTHU Data API

This module provides a centralized data manager for fetching and caching data
from data.nthusa.tw with improved architecture:

- Separation of concerns (fetching, caching, file details management)
- Configuration-based pre-fetching
- Better error handling
- Cleaner API
"""

import json
import os
import time
from typing import Optional

import httpx


class DataFetcher:
    """Handles HTTP fetching of JSON data."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def fetch_json(self, url: str) -> Optional[dict | list]:
        """
        Fetch JSON data from a URL using httpx AsyncClient.

        Args:
            url: The URL to fetch JSON data from.

        Returns:
            The parsed JSON data (dict or list), or None if an error occurs.
        """
        async with httpx.AsyncClient(http2=True) as client:
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    data = await response.aread()
                    return json.loads(data)
            except httpx.RequestError as e:
                print(f"Error fetching {url}: {e}")
                return None
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {url}: {e}")
                return None


class FileDetailsManager:
    """Manages file_details.json for tracking commit hashes."""

    def __init__(
        self, fetcher: DataFetcher, file_details_url: str, cache_expiry: int = 300
    ):
        self.fetcher = fetcher
        self.file_details_url = file_details_url
        self.cache_expiry = cache_expiry
        self._cache = {
            "data": None,
            "last_updated": None,
        }

    async def get_file_details(self) -> Optional[list[dict]]:
        """
        Get file details with automatic cache refresh.

        Returns:
            List of file detail dictionaries, or None if unavailable.
        """
        await self._update_cache()
        return self._cache["data"]

    async def _update_cache(self):
        """Update the file_details.json cache if expired or not initialized."""
        current_time = time.time()

        if (
            self._cache["data"] is None
            or self._cache["last_updated"] is None
            or (current_time - self._cache["last_updated"] > self.cache_expiry)
        ):
            raw_data = await self.fetcher.fetch_json(self.file_details_url)

            if raw_data:
                formatted_data = self._format_file_details(raw_data)
                self._cache["data"] = formatted_data
                self._cache["last_updated"] = current_time
            else:
                print("Failed to update file_details.json.")

    @staticmethod
    def _format_file_details(file_details: dict) -> list[dict]:
        """
        Format file_details.json structure to a flat list.

        Args:
            file_details: Raw JSON data from file_details.json.

        Returns:
            List of formatted file detail dictionaries.
        """
        formatted = []
        if file_details.get("file_details"):
            for section, files in file_details["file_details"].items():
                section_prefix = "" if section == "/" else section
                for file_info in files:
                    formatted.append(
                        {
                            "name": f"{section_prefix}/{file_info['name']}",
                            "last_commit": file_info["last_commit"],
                            "last_updated": file_info["last_updated"],
                        }
                    )
        return formatted

    def get_commit_hash(
        self, endpoint_name: str, file_details: list[dict]
    ) -> Optional[str]:
        """
        Get the expected commit hash for an endpoint from file details.

        Args:
            endpoint_name: The endpoint name (e.g., "/buses.json").
            file_details: List of file detail dictionaries.

        Returns:
            The commit hash string, or None if not found.
        """
        for file_info in file_details:
            if file_info["name"] == endpoint_name:
                return file_info["last_commit"]
        return None


class DataCache:
    """Manages in-memory cache for data with commit hash validation."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Optional[dict]:
        """Get cached data for a key."""
        return self._cache.get(key)

    def set(self, key: str, data: dict | list, commit_hash: str):
        """Set cached data with commit hash."""
        self._cache[key] = {
            "data": data,
            "commit_hash": commit_hash,
        }

    def is_valid(self, key: str, expected_commit_hash: str) -> bool:
        """Check if cached data is valid based on commit hash."""
        cached = self._cache.get(key)
        if not cached:
            return False
        return cached.get("commit_hash") == expected_commit_hash

    def clear(self, key: Optional[str] = None):
        """Clear cache for a specific key or all keys."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()


class NTHUDataManager:
    """
    Main data manager for NTHU data.

    Provides a centralized interface for fetching and caching data from data.nthusa.tw.
    """

    def __init__(
        self, base_url: Optional[str] = None, file_details_cache_expiry: int = 300
    ):
        """
        Initialize the data manager.

        Args:
            base_url: Base URL for data.nthusa.tw (defaults to env var or production URL).
            file_details_cache_expiry: Cache expiry time for file_details.json in seconds.
        """
        self.base_url = base_url or os.getenv("NTHU_DATA_URL", "https://data.nthusa.tw")
        self.fetcher = DataFetcher(self.base_url)
        self.file_details_manager = FileDetailsManager(
            self.fetcher,
            f"{self.base_url}/file_details.json",
            file_details_cache_expiry,
        )
        self.cache = DataCache()

    async def get(self, endpoint_name: str) -> Optional[tuple[str, dict | list]]:
        """
        Get data for an endpoint with automatic caching and commit hash validation.

        Args:
            endpoint_name: Endpoint name (e.g., "buses.json" or "dining/shops.json").

        Returns:
            Tuple of (commit_hash, data), or None if fetching fails.
        """
        # Normalize endpoint name
        endpoint_name = self._normalize_endpoint_name(endpoint_name)

        # Get file details
        file_details = await self.file_details_manager.get_file_details()
        if file_details is None:
            return None

        # Get expected commit hash
        expected_commit_hash = self.file_details_manager.get_commit_hash(
            endpoint_name, file_details
        )

        # Check cache validity
        if self.cache.is_valid(endpoint_name, expected_commit_hash):
            cached = self.cache.get(endpoint_name)
            return (cached["commit_hash"], cached["data"])

        # Fetch fresh data
        data_url = f"{self.base_url}{endpoint_name}"
        fresh_data = await self.fetcher.fetch_json(data_url)

        if fresh_data:
            self.cache.set(endpoint_name, fresh_data, expected_commit_hash)
            return (expected_commit_hash, fresh_data)
        else:
            # Try to return stale cache if available
            cached = self.cache.get(endpoint_name)
            if cached:
                return (cached["commit_hash"], cached["data"])
            return None

    async def prefetch(self, endpoints: list[str]) -> dict[str, bool]:
        """
        Pre-fetch data for multiple endpoints.

        Args:
            endpoints: List of endpoint names to pre-fetch.

        Returns:
            Dictionary mapping endpoint names to success status.
        """
        results = {}
        for endpoint in endpoints:
            result = await self.get(endpoint)
            results[endpoint] = result is not None
        return results

    async def get_file_details(self) -> Optional[list[dict]]:
        """
        Get file_details.json data.

        Returns:
            List of file detail dictionaries, or None if unavailable.
        """
        return await self.file_details_manager.get_file_details()

    def _normalize_endpoint_name(self, endpoint_name: str) -> str:
        """
        Normalize endpoint name to ensure consistent format.

        Args:
            endpoint_name: The endpoint name to normalize.

        Returns:
            Normalized endpoint name starting with '/'.
        """
        if self.base_url.endswith("/") and endpoint_name.startswith("/"):
            endpoint_name = endpoint_name[1:]
        elif not self.base_url.endswith("/") and not endpoint_name.startswith("/"):
            endpoint_name = "/" + endpoint_name
        return endpoint_name
