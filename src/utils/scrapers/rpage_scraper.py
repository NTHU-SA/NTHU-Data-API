import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.utils import cached_request


def replace_numbers_in_url(url: str, new_number: str) -> str:
    # 使用正則表達式替換 -1.php 為 -{new_number}.php
    new_url = re.sub(r"-(1)\.php", f"-{new_number}.php", url)
    return new_url


def process_date(mdate):
    return str(mdate.text) if mdate is not None else None


def process_link(url_dom, parsed_url):
    if url_dom is not None:
        title = str(url_dom.get("title"))
        href = str(url_dom.get("href"))
        # 如果 href 是相對路徑，則轉換成絕對路徑
        if href.startswith("//"):
            href = f"{parsed_url.scheme}:{href}"
        elif href.startswith("/"):
            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
    else:
        title = None
        href = None
    return title, href


def get_announcement(url: str, maxpage: int = 1) -> list:
    page_list = (
        [url] + [replace_numbers_in_url(url, str(i)) for i in range(2, maxpage + 1)]
        if maxpage > 1
        else [url]
    )
    data = []
    for url in page_list:
        response = cached_request.get(url)
        parsed_url = urlparse(url)
        soup = BeautifulSoup(response, "html.parser")
        recruitments = soup.select("#pageptlist .listBS")
        for item in recruitments:
            mdate = item.select_one(".mdate")
            date = process_date(mdate)
            url_dom = item.select_one("a")
            title, href = process_link(url_dom, parsed_url)
            data.append({"title": title, "link": href, "date": date})
    return data
