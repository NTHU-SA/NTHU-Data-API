import time

import requests
from thefuzz import fuzz, process


class Dining:
    # 餐廳及服務性廠商
    # https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw
    def __init__(self):
        self.dining_data = self.get_dining_data()
        self.last_fetch_time = time.time()

    def get_dining_data(self) -> list:
        json_url = "https://nthu-data-json.pages.dev/dining.json"
        try:
            response = requests.get(json_url)
            response.raise_for_status()  # 檢查 HTTP 請求是否成功
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {json_url}: {e}")
            return

    def get_all_building_names(self) -> list:
        building_names = []
        for building in self.dining_data:
            building_names.append(building["building"])
        return building_names

    def get_all_restaurant_names(self) -> list[str]:
        restaurant_names = []
        for building in self.dining_data:
            for restaurant in building["restaurants"]:
                restaurant_names.append(restaurant["name"])
        return restaurant_names

    def query_by_building_name(self, query_name):
        for restaurant in self.dining_data:
            if restaurant["building"] == query_name:
                return restaurant
        return {}

    def query_by_restaurant_name(self, query_name):
        res = []
        for building in self.dining_data:
            for restaurant in building["restaurants"]:
                if restaurant["name"] == query_name:
                    res.append(restaurant)
        return None if len(res) == 0 else res

    def query_by_schedule(self, query_day: str) -> list:
        scheduled_restaurants = []
        for building in self.dining_data:
            for restaurant in building["restaurants"]:
                if restaurant["schedule"][query_day] != "":
                    scheduled_restaurants.append(restaurant)
        return scheduled_restaurants

    def fuzzy_search_restaurant_by_name(self, query: str) -> list:
        restaurant_names = self.get_all_restaurant_names()
        fuzzysearch = process.extract(
            query, restaurant_names, scorer=fuzz.partial_ratio
        )
        # 只取得分數大於 50 的結果
        fuzzysearch_result = [i for i in fuzzysearch if i[1] > 50]
        # 將 fuzzysearch 的結果轉換成 dict，並且找出 data 對應的資料
        result = [
            restaurant
            for i in fuzzysearch_result
            for restaurant in self.query_by_restaurant_name(i[0])
        ]
        return result
