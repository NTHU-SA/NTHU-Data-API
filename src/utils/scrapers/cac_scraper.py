from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
from fastapi import HTTPException


def _fetch_webpage_content(url: str) -> str:
    """
    提取網頁內容。

    Args:
        url: 網頁 URL。

    Returns:
        網頁內容的文字內容。

    Raises:
        HTTPException: 當請求失敗時。
    """
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Referer": url,
    }
    try:
        response = requests.get(url, headers=default_headers)
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text
    except requests.exceptions.RequestException as e:
        status_code = response.status_code if "response" in locals() else 500
        raise HTTPException(status_code=status_code, detail=f"網頁請求失敗: {e}")


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


@cached(cache=TTLCache(maxsize=2, ttl=60 * 60))
def get_events_list(maxpage: int = 1):
    # 來源：https://cac.site.nthu.edu.tw/p/403-1549-9475.php
    url_list = [
        f"https://cac.site.nthu.edu.tw/p/403-1549-9475-{i}.php"
        for i in range(1, maxpage + 1)
    ]
    data = []
    for url in url_list:
        webpage_content = _fetch_webpage_content(url)
        soup = BeautifulSoup(webpage_content, "html.parser")
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
