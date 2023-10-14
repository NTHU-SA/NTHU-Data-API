import json

from thefuzz import fuzz, process


class Phone:
    def __init__(self):
        self.phone_data = self._load_data()

    def _load_data(self) -> dict:
        with open(f"data/directory/data/phone.json", "r", encoding="utf-8") as f:
            phones_data = json.load(f)
        return phones_data

    def all(self):
        return self.phone_data

    def get(self, query: str, field="name"):
        for i in self.phone_data:
            if i[field] == query:
                return i

    def fuzz(self, query: str):
        phone_name = [i["name"] for i in self.phone_data]
        fuzzysearch = process.extract(query, phone_name, scorer=fuzz.partial_ratio)
        # print(fuzzysearch)
        # print(process.extract(phone, phone_name, scorer=fuzz.token_sort_ratio))
        # 只取得分數大於 50 的結果
        fuzzysearch_result = [i for i in fuzzysearch if i[1] > 50]
        # 將 fuzzysearch 的結果轉換成 dict，並且找出 phone_data 對應的資料
        result = [self.get(i[0]) for i in fuzzysearch_result]
        return result


if __name__ == "__main__":
    phone = Phone()
    query = "服科所"
    print(query)
    print(phone.fuzz(query))
