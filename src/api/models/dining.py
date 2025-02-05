import time
from typing import Any, Dict, List, Optional

import requests
from thefuzz import fuzz, process


class Dining:
    """
    餐廳及服務性廠商資料
    https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw
    資料來源：https://nthu-data-json.pages.dev/dining.json
    """

    def __init__(self) -> None:
        # 若抓取資料失敗，dining_data 將初始化為空串列
        self.dining_data: List[Dict[str, Any]] = self.get_dining_data() or []
        self.last_fetch_time: float = time.time()

    def get_dining_data(self) -> Optional[List[Dict[str, Any]]]:
        """從指定 URL 取得 dining 資料，失敗則回傳 None。"""
        json_url: str = "https://nthu-data-json.pages.dev/dining.json"
        try:
            response = requests.get(json_url)
            response.raise_for_status()  # 檢查 HTTP 請求是否成功
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {json_url}: {e}")
            return None

    def get_all_building_names(self) -> List[str]:
        """回傳所有建築物名稱的串列。"""
        return [building["building"] for building in self.dining_data]

    def get_all_restaurant_names(self) -> List[str]:
        """回傳所有餐廳名稱的串列。"""
        return [
            restaurant["name"]
            for building in self.dining_data
            for restaurant in building.get("restaurants", [])
        ]

    def query_by_building_name(self, query_name: str) -> Dict[str, Any]:
        """
        根據建築物名稱查詢資料，若找不到則回傳空 dict。
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
    ) -> Optional[List[Dict[str, Any]]]:
        """
        根據餐廳名稱查詢資料，回傳符合條件的餐廳資料串列，若無符合則回傳 None。
        """
        restaurants = [
            restaurant
            for building in self.dining_data
            for restaurant in building.get("restaurants", [])
            if restaurant["name"] == query_name
        ]
        return restaurants if restaurants else None

    def query_by_schedule(self, query_day: str) -> List[Dict[str, Any]]:
        """
        根據指定的星期查詢有排定時間的餐廳，回傳符合條件的餐廳資料串列。
        """
        return [
            restaurant
            for building in self.dining_data
            for restaurant in building.get("restaurants", [])
            if restaurant.get("schedule", {}).get(query_day, "") != ""
        ]

    def fuzzy_search_restaurant_by_name(self, query: str) -> List[Dict[str, Any]]:
        """
        依據模糊搜尋比對餐廳名稱，使用 thefuzz 套件進行比對，
        並只回傳比對分數大於 50 的結果所對應的餐廳資料。
        """
        restaurant_names: List[str] = self.get_all_restaurant_names()
        fuzzy_results = process.extract(
            query, restaurant_names, scorer=fuzz.partial_ratio
        )
        # 篩選比對分數大於 50 的結果
        filtered_names = [name for name, score in fuzzy_results if score > 50]
        # 根據餐廳名稱查詢資料（可能會有多筆）
        results: List[Dict[str, Any]] = []
        for name in filtered_names:
            res = self.query_by_restaurant_name(name)
            if res:
                results.extend(res)
        return results
