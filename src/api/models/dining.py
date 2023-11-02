import requests
import re
import json
import datetime

from cachetools import cached, TTLCache


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

    def get_all_building_names(self):
        dining_data = self.get_dining_data()
        building_names = []
        for building in dining_data:
            building_names.append(building["building"])
        return building_names

    def query_by_building_name(self, query):
        dining_data = self.get_dining_data()
        for restaurant in dining_data:
            if restaurant["building"] == query:
                return restaurant
        return None

    def get_all_restaurant_names(self):
        dining_data = self.get_dining_data()
        restaurant_names = []
        for building in dining_data:
            for restaurant in building["dining"]:
                restaurant_names.append(restaurant["name"])
        return restaurant_names

    def query_by_restaurant_name(self, query):
        dining_data = self.get_dining_data()
        for building in dining_data:
            for restaurant in building["dining"]:
                if restaurant["name"] == query:
                    return restaurant
        return None

    def get_scheduled_on_saturday(self):
        dining_data = self.get_dining_data()
        saturday_restaurants = []
        for building in dining_data:
            print(building)
            for restaurant in building["restaurants"]:
                if restaurant["schedule"]["saturday"] != "":
                    saturday_restaurants.append(restaurant)
        return saturday_restaurants

    def get_scheduled_on_sunday(self):
        dining_data = self.get_dining_data()
        sunday_restaurants = []
        for building in dining_data:
            print(building)
            for restaurant in building["restaurants"]:
                if restaurant["schedule"]["sunday"] != "":
                    sunday_restaurants.append(restaurant)
        return sunday_restaurants


if __name__ == "__main__":
    dining = Dining()
    json_data = dining.get_dining_data()
    with open("data/dining_data.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
