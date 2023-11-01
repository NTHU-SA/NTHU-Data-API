import json

from thefuzz import fuzz, process


class Phone:
    def __init__(self):
        self.data = self._load_data()

    def _load_data(self) -> dict:
        with open(f"data/formatted/phone.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def _get_all_data(self, key="name"):
        for i in self.data:
            yield i["data"][key]

    def get_all(self):
        return self.data

    def get_by_id(self, query: str):
        return self.get(query, key="id")

    def get_by_data_key(self, query: str, key="name"):
        for i in self.data:
            if i["data"][key] == query:
                return i

    def fuzzy_search(self, query: str):
        name = self._get_all_data(key="name")
        fuzzysearch = process.extract(query, name, scorer=fuzz.partial_ratio)
        # 只取得分數大於 50 的結果
        fuzzysearch_result = [i for i in fuzzysearch if i[1] > 50]
        # 將 fuzzysearch 的結果轉換成 dict，並且找出 data 對應的資料
        result = [self.get_by_data_key(i[0]) for i in fuzzysearch_result]
        return result


if __name__ == "__main__":
    phone = Phone()
    query = "學科所"
    print(query)
    print(phone.fuzzy_search(query))
