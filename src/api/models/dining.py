import re
import json

import requests
from cachetools import cached, TTLCache
from thefuzz import fuzz, process


class Dining:
    # 餐廳及服務性廠商
    # https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw
    def _get_response(self, url: str):
        headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-CN;q=0.5",
            "dnt": "1",
            "referer": url,
            "sec-ch-ua": "'Chromium';v='112', 'Microsoft Edge';v='112', 'Not:A-Brand';v='99'",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "Android",
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36 Edg/112.0.1722.48",
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception("Request Error")
        response_text = response.text
        return response_text

    @cached(cache=TTLCache(maxsize=14, ttl=60 * 60))
    def get_dining_data(self):
        url = "https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw"
        res_text = self._get_response(url)
        # 將字串轉換成 json 格式
        dining_data = re.search(
            r"const restaurantsData = (\[.*?)  renderTabs", res_text, re.S
        ).group(1)
        dining_data = dining_data.replace("'", '"')
        dining_data = dining_data.replace("\n", "")
        dining_data = dining_data.replace(",  ]", "]")
        dining_data = json.loads(dining_data)
        return dining_data

    def get_all_building_names(self) -> list[str]:
        dining_data = self.get_dining_data()
        building_names = []
        for building in dining_data:
            building_names.append(building["building"])
        return building_names

    def get_all_restaurant_names(self) -> list[str]:
        dining_data = self.get_dining_data()
        restaurant_names = []
        for building in dining_data:
            for restaurant in building["restaurants"]:
                restaurant_names.append(restaurant["name"])
        return restaurant_names

    def query_by_building_name(self, query_name) -> dict:
        dining_data = self.get_dining_data()
        for restaurant in dining_data:
            if restaurant["building"] == query_name:
                return restaurant
        return None

    def query_by_restaurant_name(self, query_name):
        dining_data = self.get_dining_data()
        res = []
        for building in dining_data:
            for restaurant in building["restaurants"]:
                if restaurant["name"] == query_name:
                    res.append(restaurant)
        return None if len(res) == 0 else res

    def query_by_schedule(self, query_day: str) -> list:
        dining_data = self.get_dining_data()
        scheduled_restaurants = []
        for building in dining_data:
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


if __name__ == "__main__":
    dining = Dining()
    json_data = dining.get_dining_data()
    with open("data/dining_data.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
