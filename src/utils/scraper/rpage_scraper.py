from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.utils import cached_request


def announcement(url: str) -> list:
    """
    從 Rpage 公告頁面取得公告資料。
    Args:
        url (str): 網址。
    """
    response = cached_request.get(url)
    parsed_url = urlparse(url)

    soup = BeautifulSoup(response, "html.parser")
    recruitments = soup.select("#pageptlist .listBS")

    data = []

    for item in recruitments:
        date = item.select_one(".mdate").text if item.select_one(".mdate") else None

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
