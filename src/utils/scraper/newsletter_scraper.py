import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from cachetools import cached, TTLCache
from fastapi import HTTPException

URL_PREFIX = "https://newsletter.cc.nthu.edu.tw"


@cached(cache=TTLCache(maxsize=1, ttl=60 * 60 * 24))
def get_all_newsletters_list() -> list:
    """
    取得所有的 newsletter。
    """
    # 來源：　https://newsletter.cc.nthu.edu.tw/nthu-list/index.php/zh/home-zh-tw/lis
    url = URL_PREFIX + "/nthu-list/search.html"
    response = requests.get(url)
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
        else:
            a = None
        newsletter_list.append(
            {
                "name": a.text.strip(),
                "link": a["href"],
            }
        )
    return newsletter_list


@cached(cache=TTLCache(maxsize=32, ttl=60 * 60))
def get_selected_newsletter_list(url: str) -> str:
    """
    取得 newsletter 的內容。
    """
    response = requests.get(url)
    staus_code = response.status_code
    if staus_code != 200:
        raise HTTPException(staus_code, f"Request error: {staus_code}")
    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", {"id": "acyarchivelisting"})
    # 取得標題
    title_text = content.find("h1", {"class": "contentheading"}).text.strip()
    # 取得內容
    table = content.find("table", {"class": "contentpane"})
    newsletter_list = []
    for archiveRow in table.find_all("div", {"class": "archiveRow"}):
        a = archiveRow.find("a")
        if a is not None:
            onclick = a.get("onclick")  # 獲取連結
            match = re.search(r"openpopup\('(.*?)',", onclick)
            if match:
                link = match.group(1)
            text = a.text  # 獲取內文
        date_string = archiveRow.find("span", {"class": "sentondate"}).text.strip()
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
                "link": URL_PREFIX + link,
                "date": formatted_date,
            }
        )
    return newsletter_list
