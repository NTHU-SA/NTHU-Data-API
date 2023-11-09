# TODO: Exception handling, timeout, retry, etc.
import requests
import json


class Ckip:
    def __init__(self):
        pass

    def api(self, text: str) -> list:
        # CKIP API extract from frontend
        # API DEMO: https://ckip.iis.sinica.edu.tw/demo
        # CKIP CoreNLP API extract from frontend
        # API DEMO: https://ckip.iis.sinica.edu.tw/service/corenlp/
        url = "https://ckip.iis.sinica.edu.tw/api/corenlp/?ws=0&ner=1&wsd=2&coref=3&re=4&conparse=5"

        payload = {"text": text}
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://ckip.iis.sinica.edu.tw",
            "Referer": "https://ckip.iis.sinica.edu.tw/service/corenlp/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
        }

        result = []

        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=1
            )
            if response.status_code == 200:
                result = json.loads(response.text)
        except requests.ReadTimeout:
            print("READ TIME OUT")

        return result

    def coref(self, text: str) -> str:
        # 指代消解（Coreference Resolution）
        result = self.api(text)
        coref = result["coref"][0]
        return coref

    def recognition(self, text: str) -> str:
        # 實體辨識（Named Entity Recognition）
        result = self.api(text)
        ner = result["ner"][0]
        return ner

    def realtion(self, text: str) -> str:
        # 關係抽取（Relation Extraction）
        result = self.api(text)
        re = result["re"][0]
        return re

    def segmentation(self, text: str) -> str:
        # 斷詞系統（Word Segmentation）
        result = self.api(text)
        ws = result["ws"][0]
        return ws

    def disambiguation(self, text: str) -> str:
        # 語義辨識（Word Sense Disambiguation）
        result = self.api(text)
        wsd = result["wsd"][0]
        return wsd


if __name__ == "__main__":
    ckip = Ckip()

    def test_api_person():
        result = ckip.recognition("你知道函傳祥嗎")
        first_person = next((x["text"] for x in result if x["ner"] == "PERSON"), None)
        print(first_person)
        print(result)

    test_api_person()
