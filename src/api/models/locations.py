import json

from thefuzz import fuzz, process


class Location:
    def __init__(self, language="zh"):
        self.location_data = self._load_data(language)

    def _load_data(self, language: str) -> dict:
        with open(f"data/locations/{language}.json", "r", encoding="utf-8") as f:
            locations_data = json.load(f)
        return locations_data

    def get(self, query: str, field="id"):
        locations_data = self._load_locations_data(self.language)
        return locations_data.get(query, None)

    def fuzz(self, query: str):
        location = self.location_data.keys()
        fuzzysearch = process.extract(query, location, scorer=fuzz.partial_ratio)
        # print(fuzzysearch)
        # print(process.extract(question, question_name, scorer=fuzz.token_sort_ratio))
        # 只取得分數大於 50 的結果
        fuzzysearch_result = [i for i in fuzzysearch if i[1] > 50]
        # 將 fuzzysearch 的結果轉換成 dict，並且找出 question_data 對應的資料
        result = [self.location_data[i[0]] for i in fuzzysearch_result]
        return result


if __name__ == "__main__":
    loc = Location(language="en")
    query = "East gate"
    print(query)
    print(loc.fuzz(query))
