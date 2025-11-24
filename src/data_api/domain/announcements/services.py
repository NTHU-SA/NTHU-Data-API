"""
Announcements domain service.

Simple data fetching and filtering service for announcements.
"""

from typing import Optional

from thefuzz import fuzz

from data_api.data.manager import nthudata

# Constants
ANNOUNCEMENTS_JSON = "announcements.json"
ANNOUNCEMENTS_LIST_JSON = "announcements_list.json"
FUZZY_SEARCH_THRESHOLD = 80


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
        self,
        department: Optional[str] = None,
        title: Optional[str] = None,
        language: Optional[str] = None,
    ) -> tuple[Optional[str], list[dict]]:
        """
        Fuzzy search within the nested structure.
        Returns the original structure but with non-matching articles removed.
        """
        # 1. 取得原始資料
        result = await nthudata.get(ANNOUNCEMENTS_JSON)
        if result is None:
            return None, []

        commit_hash, raw_data = result

        filtered_results = []

        # 2. 遍歷每一個處室/來源
        for source in raw_data:
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

            # 若沒有搜尋關鍵字 (title)，則不進行模糊過濾，直接保留該處室所有文章
            if not title:
                matched_articles_with_score = [(100, art) for art in original_articles]
            else:
                # --- Level 2: 針對文章進行模糊篩選 ---
                matched_articles_with_score = []
                for article in original_articles:
                    article_title = article.get("title", "")

                    # 計算分數
                    score = fuzz.partial_ratio(title, article_title)

                    # 只有分數高於門檻的才保留
                    if score >= FUZZY_SEARCH_THRESHOLD:
                        matched_articles_with_score.append((score, article))

                # 如果這個處室在過濾後沒有任何一篇文章符合，這整個處室就不需要回傳了
                if not matched_articles_with_score:
                    continue

                # 將該處室內的文章依照分數由高到低排序 (搜尋體驗較好)
                matched_articles_with_score.sort(key=lambda x: x[0], reverse=True)

            # 3. 重組資料結構
            # 複製一份處室資訊 (避免修改到原始快取)，並替換 articles
            new_source = source.copy()
            new_source["articles"] = [item[1] for item in matched_articles_with_score]

            filtered_results.append(new_source)

        return commit_hash, filtered_results

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
