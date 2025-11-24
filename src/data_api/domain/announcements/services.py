"""
Announcements domain service.

Simple data fetching and filtering service for announcements.
"""

from typing import Optional

from data_api.data.manager import nthudata
from thefuzz import fuzz

# Constants
ANNOUNCEMENTS_JSON = "announcements.json"
ANNOUNCEMENTS_LIST_JSON = "announcements_list.json"
FUZZY_SEARCH_THRESHOLD = 60


class AnnouncementsService:
    """Service for fetching and filtering announcements."""

    async def get_announcements(
        self,
        department: Optional[str] = None,
        title: Optional[str] = None,
        language: Optional[str] = None,
    ) -> tuple[Optional[str], list[dict]]:
        """
        Get announcements with optional filtering.
        
        Returns:
            tuple: (commit_hash, filtered_announcements)
        """
        result = await nthudata.get(ANNOUNCEMENTS_JSON)
        if result is None:
            return None, []
        
        commit_hash, announcements_data = result
        
        if department:
            announcements_data = [
                announcement
                for announcement in announcements_data
                if announcement["department"] == department
            ]
        if title:
            announcements_data = [
                announcement
                for announcement in announcements_data
                if title in announcement["title"]
            ]
        if language:
            announcements_data = [
                announcement
                for announcement in announcements_data
                if announcement.get("language") == language
            ]
        
        return commit_hash, announcements_data

    async def get_announcements_list(
        self, department: Optional[str] = None
    ) -> tuple[Optional[str], list[dict]]:
        """Get announcements list (without article content)."""
        result = await nthudata.get(ANNOUNCEMENTS_LIST_JSON)
        if result is None:
            return None, []
        
        commit_hash, announcements_list = result
        
        if department:
            announcements_list = [
                announcement
                for announcement in announcements_list
                if announcement["department"] == department
            ]
        
        return commit_hash, announcements_list

    async def fuzzy_search_announcements(
        self, query: str
    ) -> tuple[Optional[str], list[dict]]:
        """Fuzzy search announcements by title."""
        result = await nthudata.get(ANNOUNCEMENTS_JSON)
        if result is None:
            return None, []
        
        commit_hash, announcements_data = result
        
        tmp_results = []
        for announcement in announcements_data:
            articles = announcement.get("articles")
            if articles is None:
                continue
            for article in articles:
                similarity = fuzz.partial_ratio(query, article["title"])
                if similarity >= FUZZY_SEARCH_THRESHOLD:
                    tmp_results.append((similarity, article))
        
        tmp_results.sort(key=lambda x: x[0], reverse=True)
        return commit_hash, [article for _, article in tmp_results]

    async def list_departments(self) -> tuple[Optional[str], list[str]]:
        """Get list of all departments with announcements."""
        result = await nthudata.get(ANNOUNCEMENTS_LIST_JSON)
        if result is None:
            return None, []
        
        commit_hash, announcements_list = result
        
        departments = {
            announcement["department"] for announcement in announcements_list
        }
        return commit_hash, sorted(departments)


# Global service instance
announcements_service = AnnouncementsService()
