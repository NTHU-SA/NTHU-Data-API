import json

from thefuzz import fuzz, process


class Question:
    def __init__(self):
        self.questions_data = self._load_data()

    def _load_data(self) -> dict:
        with open("data/questions/questions.json", "r", encoding="utf-8") as f:
            questions_data = json.load(f)
        return questions_data

    def all(self):
        return self.questions_data

    def get(self, query: str, field="ques"):
        for i in self.questions_data:
            if i[field] == query:
                return i

    def fuzz(self, query: str):
        question_name = [i["ques"] for i in self.questions_data]
        fuzzysearch = process.extract(query, question_name, scorer=fuzz.partial_ratio)
        # print(fuzzysearch)
        # print(process.extract(question, question_name, scorer=fuzz.token_sort_ratio))
        # 只取得分數大於 50 的結果
        fuzzysearch_result = [i for i in fuzzysearch if i[1] > 50]
        # 將 fuzzysearch 的結果轉換成 dict，並且找出 questions_data 對應的資料
        result = [self.get(i[0]) for i in fuzzysearch_result]
        return result


if __name__ == "__main__":
    question = Question()
    query = "怎麼超修"
    print(query)
    print(question.fuzz(query))
