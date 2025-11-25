"""
Dining domain service.

Handles business logic for dining data fetching and filtering.
"""

from datetime import datetime
from typing import Optional

from thefuzz import fuzz

from data_api.data.manager import nthudata
from data_api.domain.dining import enums

JSON_PATH = "dining.json"
FUZZY_SEARCH_THRESHOLD = 60


def is_restaurant_open(restaurant: dict, day: str) -> bool:
    """
    Check if restaurant is open on specified day.

    Args:
        restaurant: Restaurant data dict
        day: Day of week in English lowercase

    Returns:
        True if restaurant may be open, False if definitely closed
    """
    note = restaurant.get("note", "").lower()
    for keyword in enums.DiningScheduleKeyword.BREAK_KEYWORDS:
        for day_zh in enums.DiningScheduleKeyword.DAY_EN_TO_ZH.get(day, []):
            if keyword in note and day_zh in note:
                return False
    return True


class DiningService:
    """Service for dining data operations."""

    async def get_dining_data(
        self, building_name: Optional[str] = None, restaurant_name: Optional[str] = None
    ) -> tuple[Optional[str], list[dict]]:
        """Get dining data with optional building filter."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, dining_data = result

        filtered = []

        for b in dining_data:
            # 篩建築物
            if building_name and b["building"] != building_name:
                continue
            # 篩餐廳
            restaurants = b["restaurants"]
            if restaurant_name:
                restaurants = [r for r in restaurants if restaurant_name in r["name"]]

            # 沒餐廳就不要放進去，免得空殼 building 出現
            if restaurants:
                filtered.append(
                    {
                        **b,
                        "restaurants": restaurants,
                    }
                )

        dining_data = filtered

        return commit_hash, dining_data

    async def get_open_restaurants(self, schedule: str) -> tuple[Optional[str], list[dict]]:
        """Get currently open restaurants based on schedule."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, dining_data = result

        open_restaurants = []
        for building in dining_data:
            for restaurant in building["restaurants"]:
                if schedule == "today":
                    current_day = datetime.now().strftime("%A").lower()
                    if current_day in ["saturday", "sunday"]:
                        day = current_day
                    else:
                        day = "weekday"
                else:
                    day = schedule

                if is_restaurant_open(restaurant, day):
                    open_restaurants.append(restaurant)

        return commit_hash, open_restaurants

    async def fuzzy_search_dining_data(
        self, building_name: Optional[str] = None, restaurant_name: Optional[str] = None
    ) -> tuple[Optional[str], list[dict]]:
        """
        Fuzzy search dining data while maintaining the nested structure.
        Returns: list[DiningBuilding]
        """
        result = await nthudata.get(JSON_PATH)
        if result is None:
            return None, []

        commit_hash, raw_data = result
        filtered_results = []

        # 2. 遍歷每一棟建築
        for building in raw_data:
            # --- Level 1: 建築名稱篩選 ---
            # 如果有給 building_name，就先檢查建築名稱是否符合
            if building_name:
                b_score = fuzz.partial_ratio(building_name, building.get("building", ""))
                if b_score < FUZZY_SEARCH_THRESHOLD:
                    # 建築名稱不符合，直接跳過整棟
                    continue

            # 取得該建築內的所有餐廳
            original_restaurants = building.get("restaurants", [])
            matched_restaurants = []

            # --- Level 2: 餐廳名稱篩選 ---
            if restaurant_name:
                # 如果有搜餐廳名，則過濾內部的餐廳
                temp_scores = []
                for restaurant in original_restaurants:
                    r_score = fuzz.partial_ratio(restaurant_name, restaurant.get("name", ""))
                    if r_score >= FUZZY_SEARCH_THRESHOLD:
                        temp_scores.append((r_score, restaurant))

                # 如果這棟樓裡面，沒有任何一家餐廳符合搜尋，這棟樓就不用回傳了
                # (除非使用者只搜了建築名，沒搜餐廳名，那下面 else 會處理)
                if not temp_scores:
                    continue

                # 依照分數排序內部的餐廳
                temp_scores.sort(key=lambda x: x[0], reverse=True)
                matched_restaurants = [item[1] for item in temp_scores]

            else:
                # 如果沒有搜餐廳名 (只搜建築)，則保留該建築內所有餐廳
                matched_restaurants = original_restaurants

            # 3. 重組資料結構
            # 複製一份建築資料，避免改到快取
            new_building = building.copy()
            new_building["restaurants"] = matched_restaurants

            filtered_results.append(new_building)

        return commit_hash, filtered_results


# Global service instance
dining_service = DiningService()
