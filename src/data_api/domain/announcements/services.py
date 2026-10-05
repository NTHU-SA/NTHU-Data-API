"""
Announcements domain service.

Simple data fetching and filtering service for announcements.
"""

import re
from typing import Optional

from thefuzz import fuzz

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.utils.search import fuzzy_matches

# Constants
ANNOUNCEMENTS_JSON = "announcements.json"
ANNOUNCEMENTS_LIST_JSON = "announcements_list.json"
FUZZY_SEARCH_THRESHOLD = 80
DATASET_UNAVAILABLE = "Dataset temporarily unavailable"


def _matches_source_url(link: str, url: str) -> bool:
    def split_url(value: str) -> tuple[bool, str, str]:
        scheme = re.match(r"https?://", value, re.IGNORECASE)
        without_scheme = value[scheme.end() :] if scheme else value
        parts = re.split(r"([/?#])", without_scheme, maxsplit=1)
        return bool(scheme), parts[0], "".join(parts[1:])

    _, link_host, link_tail = split_url(link)
    has_scheme, query_host, query_tail = split_url(url)
    normalized_link = link_host.casefold() + link_tail
    if has_scheme or (
        query_host.casefold() in link_host.casefold() and (not query_tail or "." in query_host)
    ):
        url = query_host.casefold() + query_tail
    return url in normalized_link


class AnnouncementsService:
    """Service for fetching and filtering announcements."""

    async def get_announcements(
        self,
        department: Optional[str] = None,
        title: Optional[str] = None,
        language: Optional[str] = None,
        url: Optional[str] = None,
    ) -> tuple[Optional[str], list[dict]]:
        """
        Get announcements with optional filtering.

        Returns:
            tuple: (commit_hash, filtered_announcements)
        """
        result = await nthudata.get(ANNOUNCEMENTS_JSON)
        if result is None:
            raise DataNotAvailableException(DATASET_UNAVAILABLE)

        commit_hash, announcements_data = result

        if url:
            announcements_data = [
                announcement
                for announcement in announcements_data
                if _matches_source_url(announcement["link"], url)
            ]
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
            raise DataNotAvailableException(DATASET_UNAVAILABLE)

        commit_hash, announcements_list = result

        if department:
            announcements_list = [
                announcement
                for announcement in announcements_list
                if announcement["department"] == department
            ]

        return commit_hash, announcements_list

    async def fuzzy_search_announcements(
        self,
        department: Optional[str] = None,
        title: Optional[str] = None,
        language: Optional[str] = None,
        url: Optional[str] = None,
    ) -> tuple[Optional[str], list[dict]]:
        """
        Fuzzy search within the nested structure.
        Returns the original structure but with non-matching articles removed.
        """
        # 1. 取得原始資料
        result = await nthudata.get(ANNOUNCEMENTS_JSON)
        if result is None:
            raise DataNotAvailableException(DATASET_UNAVAILABLE)

        commit_hash, raw_data = result

        filtered_results = []

        # 2. 遍歷每一個處室/來源
        for source in raw_data:
            if url and not _matches_source_url(source["link"], url):
                continue

            # 如果使用者指定了語言，不符合的整包直接跳過
            if language and source.get("language") != language:
                continue

            # 如果使用者指定了部門，模糊比對不符合的整包直接跳過
            if department:
                dept_name = source.get("department", "")
                score = fuzz.partial_ratio(department, dept_name)
                if score < FUZZY_SEARCH_THRESHOLD:
                    continue

            # 取出該處室的所有文章
            original_articles = source.get("articles", [])

            matched_articles = list(original_articles)
            if title:
                matched_articles = fuzzy_matches(
                    original_articles, title, "title", FUZZY_SEARCH_THRESHOLD
                )
                if not matched_articles:
                    continue

            # 3. 重組資料結構
            # 複製一份處室資訊 (避免修改到原始快取)，並替換 articles
            new_source = source.copy()
            new_source["articles"] = matched_articles

            filtered_results.append(new_source)

        return commit_hash, filtered_results

    async def list_departments(self) -> tuple[Optional[str], list[str]]:
        """Get list of all departments with announcements."""
        commit_hash, announcements_list = await self.get_announcements_list()
        departments = {announcement["department"] for announcement in announcements_list}
        return commit_hash, sorted(departments)


# Global service instance
announcements_service = AnnouncementsService()
