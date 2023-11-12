import json
import re

from thefuzz import fuzz, process

from src.utils import cached_request


class Dining:
    # 餐廳及服務性廠商
    # https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw

    def get_dining_data(self) -> list:
        url = "https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw"
        res_text = cached_request.get(url)
        # 將字串轉換成 json 格式
        dining_data = re.search(
            r"const restaurantsData = (\[.*?) {2}renderTabs", res_text, re.S
        )
        if dining_data is not None:
            dining_data = dining_data.group(1)
        else:
            return []
        dining_data = dining_data.replace("'", '"')
        dining_data = dining_data.replace("\n", "")
        dining_data = dining_data.replace(",  ]", "]")
        dining_data = json.loads(dining_data)
        return dining_data

    def get_all_building_names(self) -> list:
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

    def query_by_building_name(self, query_name):
        dining_data = self.get_dining_data()
        for restaurant in dining_data:
            if restaurant["building"] == query_name:
                return restaurant
        return {}

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
