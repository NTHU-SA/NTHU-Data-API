import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.utils import cached_request


def replace_numbers_in_url(url: str, new_number: str) -> str:
    # 使用正則表達式替換 -1.php 為 -{new_number}.php
    new_url = re.sub(r"-(1)\.php", f"-{new_number}.php", url)
    return new_url


def announcement(url: str, maxpage: int = 1) -> list:
    """
    從 Rpage 公告頁面取得公告資料。
    Args:
        url (str): 網址。
    """
    page_list = []
    page_list.append(url)
    # 如果 maxpage 大於 1，就把其他頁面的網址加入 page_list
    if maxpage > 1:
        for i in range(2, maxpage + 1):
            page_list.append(replace_numbers_in_url(url, str(i)))

    data = []

    for url in page_list:
        response = cached_request.get(url)
        parsed_url = urlparse(url)

        soup = BeautifulSoup(response, "html.parser")
        recruitments = soup.select("#pageptlist .listBS")
        for item in recruitments:
            mdate = item.select_one(".mdate")
            date = str(mdate.text) if mdate is not None else None
            url_dom = item.select_one("a")
            if url_dom is not None:
                title = str(url_dom.get("title"))
                href = str(url_dom.get("href"))
                # 網址解析
                # 如果原始網址以 // 或 / 起始（不完整），就加上完整網址的協定
                if href.startswith("//"):
                    href = f"{parsed_url.scheme}:{href}"
                elif href.startswith("/"):
                    href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
            else:
                title = None
                href = None

            data.append(
                {
                    "title": title,
                    "link": href,
                    "date": date,
                }
            )

    return data
