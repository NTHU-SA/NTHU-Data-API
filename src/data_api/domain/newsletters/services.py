"""
Newsletters domain service.

Handles newsletter data fetching.
"""

from typing import Optional

from data_api.data.manager import nthudata

JSON_PATH = "newsletters.json"


class NewslettersService:
    """Service for newsletter data operations."""

    async def get_all_newsletters(self) -> tuple[Optional[str], list[dict]]:
        """Get all newsletters."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []
        return result

    async def get_newsletter_by_name(
        self, name: str
    ) -> tuple[Optional[str], Optional[dict]]:
        """Get newsletter by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, None

        commit_hash, newsletter_data = result
        for newsletter in newsletter_data:
            if newsletter["name"] == name:
                return commit_hash, newsletter
        return commit_hash, None


# Global service instance
newsletters_service = NewslettersService()
