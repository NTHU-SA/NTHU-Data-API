from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.utils import cached_requests


def process_img(dimg, parsed_url):
    if dimg is not None:
        img = str(dimg.find("img").get("src"))
        if img.startswith("//"):
            img = f"{parsed_url.scheme}:{img}"
        elif img.startswith("/"):
            img = f"{parsed_url.scheme}://{parsed_url.netloc}{img}"
    else:
        img = None
    return img


def process_link(a, parsed_url):
    if a is not None:
        href = str(a.get("href"))
        title = str(a.get("title"))
        if href.startswith("//"):
            href = f"{parsed_url.scheme}:{href}"
        elif href.startswith("/"):
            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
    else:
        href = None
        title = None
    return href, title


def get_events_list(maxpage: int = 1):
    # 來源：https://cac.site.nthu.edu.tw/p/403-1549-9475.php
    url_list = [
        f"https://cac.site.nthu.edu.tw/p/403-1549-9475-{i}.php"
        for i in range(1, maxpage + 1)
    ]
    data = []
    for url in url_list:
        response, using_cache = cached_requests.get(url, update=True, auto_headers=True)
        soup = BeautifulSoup(response, "html.parser")
        cac_activity = soup.select("#pageptlist .d-item")
        parsed_url = urlparse(url)
        for item in cac_activity:
            dimg = item.select_one("div.d-img")
            a = dimg.find("a") if dimg is not None else None
            img = process_img(dimg, parsed_url)
            href, title = process_link(a, parsed_url)
            data.append(
                {"title": title, "link": href, "image": img, "unix_timestamp": None}
            )
    return data
