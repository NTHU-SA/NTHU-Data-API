import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import requests
from thefuzz import fuzz, process

from src.api.schemas.dining import DiningRestaurant, DiningSceduleKeyword

JSON_URL = os.getenv("NTHU_DATA_URL", "https://data.nthusa.tw") + "/dining.json"
FUZZY_MATCH_THRESHOLD = 50
DATA_TTL_HOURS = 4  # 資料存活時間 (小時)


class Dining:
    """
    餐廳及服務性廠商資料
    https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw
    """

    def __init__(self) -> None:
        """
        初始化 Dining 類別。

        載入餐廳資料並建立快取，若快取資料過期或尚未初始化，則會從遠端端點重新獲取資料。
        """
        self.dining_data: List[DiningRestaurant] = []
        self._restaurant_names: Set[str] = set()
        self._building_names: Set[str] = set()
        self._last_updated_time: Optional[float] = None  # 上次資料更新時間戳記
        self._initialize_data()

    def _initialize_data(self) -> None:
        """
        初始化餐廳資料。

        檢查快取資料是否過期，若過期或尚未初始化，則從遠端 JSON 端點獲取最新的餐廳資料。
        資料獲取成功後，會建立快取並更新上次更新時間戳記。
        """
        if not self.dining_data or self._is_data_expired():
            data = self._fetch_dining_data()
            if data:
                self.dining_data = data
                self._build_caches()
                self._last_updated_time = time.time()  # 更新時間戳記

    def _is_data_expired(self) -> bool:
        """
        檢查快取資料是否過期。

        根據設定的 `DATA_TTL_HOURS` 判斷資料是否需要更新。

        Returns:
            bool: 若資料已過期或尚未初始化，則返回 True，否則返回 False。
        """
        if self._last_updated_time is None:
            return True  # 尚未載入過資料
        return time.time() - self._last_updated_time > DATA_TTL_HOURS * 3600

    def _build_caches(self) -> None:
        """
        建立餐廳名稱與建築物名稱的快取集合。

        快取用於加速查詢操作，避免重複迭代整個餐廳資料列表。
        """
        self._restaurant_names = {
            restaurant["name"]
            for building in self.dining_data
            for restaurant in building.get("restaurants", [])
        }
        self._building_names = {building["building"] for building in self.dining_data}

    def _fetch_dining_data(self) -> Optional[List[DiningRestaurant]]:
        """
        從遠端 JSON 端點獲取餐廳資料。

        使用 `requests` 函式庫向 `JSON_URL` 發送 GET 請求，並處理可能的連線錯誤。

        Returns:
            Optional[List[DiningRestaurant]]: 若成功獲取資料，則返回餐廳資料列表，否則返回 None。
        """
        try:
            response = requests.get(
                JSON_URL,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()  # 針對 HTTP 錯誤狀態碼拋出例外
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch dining data: {e}")
            return None

    @property
    def all_building_names(self) -> List[str]:
        """
        取得所有餐廳所在建築物名稱列表。

        Returns:
            List[str]: 包含所有建築物名稱的列表。
        """
        return list(self._building_names)

    @property
    def all_restaurant_names(self) -> List[str]:
        """
        取得所有餐廳名稱列表。

        Returns:
            List[str]: 包含所有餐廳名稱的列表。
        """
        return list(self._restaurant_names)

    def query_by_building_name(self, query_name: str) -> Dict[str, Any]:
        """
        根據建築物名稱查詢餐廳資料。

        Args:
            query_name (str): 要查詢的建築物名稱。

        Returns:
            Dict[str, Any]: 若找到符合的建築物，則返回包含該建築物餐廳資料的字典，否則返回空字典。
        """
        return next(
            (
                building
                for building in self.dining_data
                if building["building"] == query_name
            ),
            {},
        )

    def query_by_restaurant_name(
        self, query_name: str
    ) -> Optional[List[DiningRestaurant]]:
        """
        根據餐廳名稱查詢餐廳資料。

        Args:
            query_name (str): 要查詢的餐廳名稱。

        Returns:
            Optional[List[DiningRestaurant]]: 若找到符合的餐廳，則返回包含餐廳資料的列表，
                                            若餐廳名稱不在快取中或找不到餐廳，則返回空列表。
        """
        if query_name not in self._restaurant_names:
            return []

        restaurants = [
            restaurant
            for building in self.dining_data
            for restaurant in building.get("restaurants", [])
            if restaurant["name"] == query_name
        ]
        return restaurants or []  # 更簡潔的寫法，與 `if restaurants else []` 等效

    def is_restaurant_open(self, restaurant: DiningRestaurant, day: str) -> bool:
        """
        判斷餐廳在指定日期是否營業。

        分析餐廳資料中的 'note' 欄位，檢查是否包含表示特定日期休息的關鍵字。

        Args:
            restaurant (DiningRestaurant): 要檢查的餐廳資料。
            day (str): 要查詢的星期幾，使用英文小寫 (例如：'monday')。

        Returns:
            bool: 若餐廳在指定日期可能營業，則返回 True，否則返回 False。
        """
        note = restaurant.get("note", "").lower()
        for keyword in DiningSceduleKeyword.BREAK_KEYWORDS:
            for day_zh in DiningSceduleKeyword.DAY_EN_TO_ZH.get(day, []):
                if keyword in note and day_zh in note:
                    return False  # 找到休息關鍵字，判斷為休息
        return True  # 未找到休息關鍵字，判斷為營業

    def get_open_restaurants_by_day_of_week(
        self, query_day: str
    ) -> List[DiningRestaurant]:
        """
        取得在指定星期幾營業的餐廳列表。

        Args:
            query_day (str): 要查詢的星期幾，使用英文小寫 (例如：'monday')。

        Returns:
            List[DiningRestaurant]: 返回在指定星期幾可能營業的餐廳列表。
        """
        if query_day == "today":
            query_day = datetime.now().strftime("%A").lower()
        return [
            restaurant
            for building in self.dining_data
            for restaurant in building.get("restaurants", [])
            if self.is_restaurant_open(restaurant, query_day)
        ]

    def fuzzy_search_restaurant_by_name(self, query: str) -> List[DiningRestaurant]:
        """
        根據餐廳名稱進行模糊搜尋。

        使用 `thefuzz` 函式庫進行模糊比對，找出與查詢字串相似的餐廳名稱。

        Args:
            query (str): 模糊搜尋的查詢字串。

        Returns:
            List[DiningRestaurant]: 返回與查詢字串模糊匹配的餐廳列表，
                                     結果會根據相似度排序，並篩選掉低於閾值的結果。
                                     若查詢字串為空或找不到匹配的餐廳，則返回空列表。
        """
        if not query:
            return []

        restaurant_names = list(self._restaurant_names)
        fuzzy_results = process.extract(
            query,
            restaurant_names,
            scorer=fuzz.partial_ratio,
            limit=10,  # 限制結果數量以提升效能
        )

        results: List[DiningRestaurant] = []
        for name, score in fuzzy_results:
            if score >= FUZZY_MATCH_THRESHOLD:
                results.extend(self.query_by_restaurant_name(name))
        return results
