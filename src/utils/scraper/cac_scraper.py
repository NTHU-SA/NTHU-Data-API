from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.utils import cached_request


def get_events_list(maxpage: int = 1):
    # 來源：https://cac.site.nthu.edu.tw/p/403-1549-9475.php
    url_list = []
    for i in range(1, maxpage + 1):
        url_list.append(f"https://cac.site.nthu.edu.tw/p/403-1549-9475-{i}.php")
    data = []
    for url in url_list:
        response = cached_request.get(url)
        soup = BeautifulSoup(response, "html.parser")
        cac_activity = soup.select("#pageptlist .d-item")
        # 取得網址的 domain
        parsed_url = urlparse(url)
        for item in cac_activity:
            # 找到 a 元素，取出 href 和 title 屬性
            # 找到 img 元素，取出 src 屬性
            dimg = item.select_one("div.d-img")
            if dimg is not None:
                a = dimg.find("a")
                img = str(dimg.find("img").get("src"))
                if img.startswith("//"):
                    img = f"{parsed_url.scheme}:{img}"
                elif img.startswith("/"):
                    img = f"{parsed_url.scheme}://{parsed_url.netloc}{img}"
            else:
                a = None
                img = None
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
            data.append(
                {
                    "title": title,
                    "link": href,
                    "image": img,
                }
            )
    return data
