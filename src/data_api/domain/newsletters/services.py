"""
Newsletters domain service.

Handles newsletter data fetching.
"""

from typing import Optional

from thefuzz import fuzz

from data_api.data.manager import nthudata
from data_api.data.nthudata import NTHUDataManager
from data_api.utils.search import fuzzy_matches

JSON_PATH = "newsletters.json"
FUZZY_SEARCH_THRESHOLD = 60


class NewslettersService:
    """Service for newsletter data operations."""

    def __init__(self, manager: NTHUDataManager = nthudata):
        self.manager = manager

    async def get_all_newsletters(self) -> tuple[Optional[str], list[dict]]:
        """Get all newsletters."""
        return await self.manager.get(JSON_PATH)

    @staticmethod
    def _matches_newsletter_name(newsletter_name: str, query: Optional[str], fuzzy: bool) -> bool:
        if not query:
            return True
        if fuzzy:
            return fuzz.partial_ratio(query, newsletter_name) >= FUZZY_SEARCH_THRESHOLD
        return newsletter_name == query

    @staticmethod
    def _filter_newsletter_articles(
        articles: list[dict], title: Optional[str], fuzzy: bool
    ) -> list[dict]:
        if not title:
            return list(articles)
        if fuzzy:
            return fuzzy_matches(articles, title, "title", FUZZY_SEARCH_THRESHOLD)
        return [article for article in articles if title in (article.get("title") or "")]

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
            if not self._matches_newsletter_name(newsletter["name"], name, fuzzy):
                continue

            articles = self._filter_newsletter_articles(newsletter["articles"], title, fuzzy)
            if title and not articles:
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


# Global service instance
newsletters_service = NewslettersService()
