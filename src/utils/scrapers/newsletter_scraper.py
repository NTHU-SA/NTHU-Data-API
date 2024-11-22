import re
from datetime import datetime

from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
from fastapi import HTTPException

from src.utils import cached_requests

URL_PREFIX = "https://newsletter.cc.nthu.edu.tw"


@cached(cache=TTLCache(maxsize=1, ttl=60 * 60 * 24))
def get_all_newsletters_list() -> list:
    """
    取得所有的 newsletter。
    """
    # 來源：　https://newsletter.cc.nthu.edu.tw/nthu-list/index.php/zh/home-zh-tw/lis
    url = URL_PREFIX + "/nthu-list/search.html"
    response, _using_cache = cached_requests.get(url, update=True, auto_headers=True)
    staus_code = response.status_code
    if staus_code != 200:
        raise HTTPException(staus_code, f"Request error: {staus_code}")
    response.encoding = "big5"  # 設置編碼為 UTF-8
    soup = BeautifulSoup(response.text, "html.parser")
    gallery = soup.find("div", {"class": "gallery"})
    newsletter_list = []
    for li in gallery.find_all("li"):
        h3 = li.find("h3")
        if h3 is not None:
            a = h3.find("a")
            newsletter_list.append(
                {
                    "name": a.text.strip(),
                    "link": a["href"],
                }
            )
    return newsletter_list


@cached(cache=TTLCache(maxsize=32, ttl=60 * 60))
def get_selected_newsletter_list(url: str) -> list:
    """
    取得 newsletter 的內容。
    """
    if url.startswith(URL_PREFIX):
        response, _using_cache = cached_requests.get(url, update=True, auto_headers=True)
    else:
        raise HTTPException(400, "Invalid URL")
    staus_code = response.status_code
    if staus_code != 200:
        raise HTTPException(staus_code, f"Request error: {staus_code}")
    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", {"id": "acyarchivelisting"})
    if content is None:
        raise HTTPException(404, "Not found")
    table = content.find("table", {"class": "contentpane"})
    newsletter_list = []
    for archive_row in table.find_all("div", {"class": "archiveRow"}):
        text = None
        link = None

        a = archive_row.find("a")
        if a is not None:
            onclick = a.get("onclick")  # 獲取連結
            match = re.search(r"openpopup\('(.*?)',", onclick)
            if match:
                link = URL_PREFIX + match.group(1)
            text = a.text  # 獲取內文
        date_string = archive_row.find("span", {"class": "sentondate"}).text.strip()
        month_mapping = {
            " 一月 ": " Jan ",
            " 二月 ": " Feb ",
            " 三月 ": " Mar ",
            " 四月 ": " Apr ",
            " 五月 ": " May ",
            " 六月 ": " Jun ",
            " 七月 ": " Jul ",
            " 八月 ": " Aug ",
            " 九月 ": " Sep ",
            " 十月 ": " Oct ",
            " 十一月 ": " Nov ",
            " 十二月 ": " Dec ",
        }  # 前後空格是為了避免誤判
        date_string = date_string.replace("Sent on ", "")
        for zh_month, en_month in month_mapping.items():
            date_string = date_string.replace(zh_month, en_month)

        date_object = datetime.strptime(date_string, "%d %b %Y")
        formatted_date = date_object.strftime("%Y-%m-%d")
        newsletter_list.append(
            {
                "title": text,
                "link": link,
                "date": formatted_date,
            }
        )
    return newsletter_list
