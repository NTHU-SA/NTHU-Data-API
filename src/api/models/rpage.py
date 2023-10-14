import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class Rpage:
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
        response_text = response.text
        response_code = response.status_code
        return response_text, response_code

    def crawler(self, url: str):
        # requests.packages.urllib3.disable_warnings()  # 關閉警告
        # requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = "ALL:@SECLEVEL=1"

        data = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36"
        }
        response, code = self._get_response(url)
        soup = BeautifulSoup(response, "html.parser")
        recruitments = soup.select("#pageptlist .listBS")

        # print(soup.prettify())
        # print(recruitments)

        # 取得網址的 domain
        domain = urlparse(url).netloc

        for item in recruitments:
            mdate_before_element = item.select_one(".mdate.before")
            mdate_after_element = item.select_one(".mdate.after")

            if mdate_before_element:
                date = item.select_one(".mdate.before")
                if date is not None:
                    date = date.text
            elif mdate_after_element:
                date = item.select_one(".mdate.after")
                if date is not None:
                    date = date.text
            else:
                date = None

            url_dom = item.select_one("a")

            if url_dom is not None:
                title = str(url_dom.get("title"))
                href = str(url_dom.get("href"))
                # 網址解析
                # 如果原始網址沒有協定，就加上完整網址的協定
                if href.startswith("http") and not href.startswith("https"):
                    href = f"https://{domain}/{href}"
                # 如果原始網址沒有 domain，就加上完整網址的 domain
                elif not href.startswith("http"):
                    href = f"https://{domain}/{href}"
            else:
                title = None
                href = None

            data.append({"title": title, "date": date, "url": href})
        # print(f"{data}\n")
        return data, code
