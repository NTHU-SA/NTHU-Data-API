# 使用 thefuzz 進行模糊搜尋
from thefuzz import fuzz, process


class FuzzySearch:
    def __init__(self, data):
        self.data = data

    def search(self, query):
        return process.extract(query, self.data, limit=3)

    def search_one(self, query):
        # 給定一個 query 在完整的 data 中搜尋，回傳最相近的結果
        return process.extractOne(query, self.data)


import json

with open("data/directory/data/phone.json", "r", encoding="utf-8") as f:
    data = json.load(f)

name = []

for i in data:
    name.append(i["name"])

fuzzysearch = FuzzySearch(["apple", "banana", "orange", "watermelon", "pineapple"])
print(fuzzysearch.search("appel"))

fuzzysearch = FuzzySearch(name)
print(fuzzysearch.search_one("繼通中心"))
