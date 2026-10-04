"""
Newsletters domain service.

Handles newsletter data fetching.
"""

from typing import Optional

from thefuzz import fuzz

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.utils.search import fuzzy_matches

JSON_PATH = "newsletters.json"
FUZZY_SEARCH_THRESHOLD = 80


class NewslettersService:
    """Service for newsletter data operations."""

    async def get_all_newsletters(self) -> tuple[Optional[str], list[dict]]:
        """Get all newsletters."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")
        return result

    async def get_newsletters(
        self,
        name: Optional[str] = None,
        title: Optional[str] = None,
        fuzzy: bool = True,
    ) -> tuple[Optional[str], list[dict]]:
        """Filter sources and nested articles without modifying cached data."""
        commit_hash, newsletters = await self.get_all_newsletters()
        filtered = []
        for newsletter in newsletters:
            if name:
                if fuzzy:
                    if fuzz.partial_ratio(name, newsletter["name"]) < FUZZY_SEARCH_THRESHOLD:
                        continue
                elif newsletter["name"] != name:
                    continue

            articles = list(newsletter["articles"])
            if title:
                if fuzzy:
                    articles = fuzzy_matches(articles, title, "title", FUZZY_SEARCH_THRESHOLD)
                else:
                    articles = [
                        article for article in articles if title in (article.get("title") or "")
                    ]
                if not articles:
                    continue

            filtered.append({**newsletter, "articles": articles})
        return commit_hash, filtered

    async def get_newsletter_sources(
        self, name: Optional[str] = None
    ) -> tuple[Optional[str], list[dict]]:
        """Get source metadata without articles, optionally matching an exact name."""
        commit_hash, newsletters = await self.get_all_newsletters()
        sources = [
            {key: newsletter[key] for key in ("name", "link", "details")}
            for newsletter in newsletters
            if not name or newsletter["name"] == name
        ]
        return commit_hash, sources

    async def get_newsletter_by_name(self, name: str) -> tuple[Optional[str], Optional[dict]]:
        """Get newsletter by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException("Dataset temporarily unavailable")

        commit_hash, newsletter_data = result
        for newsletter in newsletter_data:
            if newsletter["name"] == name:
                return commit_hash, newsletter
        return commit_hash, None


# Global service instance
newsletters_service = NewslettersService()
