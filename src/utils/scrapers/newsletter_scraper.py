import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
from fastapi import HTTPException

URL_PREFIX = "https://newsletter.cc.nthu.edu.tw"
CACHE_TTL_DAY = 60 * 60 * 24
CACHE_TTL_HOUR = 60 * 60
MONTH_MAPPING = {
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
}


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


def _parse_newsletter_list_from_gallery(soup: BeautifulSoup) -> list:
    """
    從 BeautifulSoup 物件中解析電子報列表。

    Args:
        soup: BeautifulSoup 物件，已解析的網頁內容。

    Returns:
        一個包含電子報資訊的列表。
    """
    gallery = soup.find("div", {"class": "gallery"})
    if not gallery:
        return []
    newsletter_list = []
    for li in gallery.find_all("li"):
        h3 = li.find("h3")
        if h3:
            a = h3.find("a")
            newsletter_list.append(
                {
                    "name": a.text.strip(),
                    "link": a["href"],
                }
            )
    return newsletter_list


@cached(cache=TTLCache(maxsize=1, ttl=CACHE_TTL_DAY))
def get_all_newsletters_list() -> list:
    """
    從清華大學電子報網站取得所有電子報列表。

    快取設定為一天，避免重複請求。

    Returns:
        一個包含所有電子報資訊的列表，每個元素為一個字典，包含 'name' (電子報名稱) 和 'link' (電子報連結)。

    Raises:
        HTTPException: 當 HTTP 請求失敗時。
    """
    url = f"{URL_PREFIX}/nthu-list/search.html"
    soup = _fetch_webpage_content(url)
    return _parse_newsletter_list_from_gallery(soup)


def _parse_date_string(date_string: str) -> str | None:
    """
    解析日期字串並格式化為 YYYY-MM-DD。

    Args:
        date_string: 原始日期字串。

    Returns:
        格式化後的日期字串 (YYYY-MM-DD)，如果解析失敗則返回 None。
    """
    if not date_string:
        return None
    date_string = date_string.replace("Sent on ", "")
    for zh_month, en_month in MONTH_MAPPING.items():
        date_string = date_string.replace(zh_month, en_month)
    try:
        date_object = datetime.strptime(date_string, "%d %b %Y")
        return date_object.strftime("%Y-%m-%d")
    except ValueError:
        return None


def _parse_newsletter_content_list(soup: BeautifulSoup) -> list:
    """
    從 BeautifulSoup 物件中解析單期電子報內容列表。

    Args:
        soup: BeautifulSoup 物件，已解析的網頁內容。

    Returns:
        一個包含電子報內容資訊的列表。

    Raises:
        HTTPException: 當找不到電子報內容時。
    """
    content = soup.find("div", {"id": "acyarchivelisting"})
    if not content:
        raise HTTPException(status_code=404, detail="找不到電子報內容")

    table = content.find("table", {"class": "contentpane"})
    if not table:
        return []

    newsletter_content_list = []
    for archive_row in table.find_all("div", {"class": "archiveRow"}):
        title = None
        link = None
        date_string_element = archive_row.find("span", {"class": "sentondate"})
        date_string = date_string_element.text.strip() if date_string_element else None

        a_tag = archive_row.find("a")
        if a_tag:
            title = a_tag.text.strip()
            onclick_attr = a_tag.get("onclick")
            if onclick_attr:
                match = re.search(r"openpopup\('(.*?)',", onclick_attr)
                if match:
                    link = f"{URL_PREFIX}{match.group(1)}"

        formatted_date = _parse_date_string(date_string)

        newsletter_content_list.append(
            {
                "title": title,
                "link": link,
                "date": formatted_date,
            }
        )
    return newsletter_content_list


@cached(cache=TTLCache(maxsize=32, ttl=CACHE_TTL_HOUR))
def get_selected_newsletter_list(url: str) -> list:
    """
    從指定的電子報連結取得該期電子報的內容列表。

    快取設定為一小時，避免重複請求。

    Args:
        url: 電子報的網址。

    Returns:
        一個包含該期電子報內容資訊的列表，每個元素為一個字典，包含 'title' (文章標題)、'link' (文章連結) 和 'date' (發布日期，格式為 YYYY-MM-DD)。

    Raises:
        HTTPException:
            - 當 URL 無效時 (400)。
            - 當 HTTP 請求失敗時。
            - 當在網頁內容中找不到文章列表時 (404)。
            - 當解析日期字串失敗時 (500)。
    """
    if not url.startswith(URL_PREFIX):
        raise HTTPException(status_code=400, detail="無效的電子報 URL")
    try:
        webpage_content = _fetch_webpage_content(url)
        soup = BeautifulSoup(webpage_content, "html.parser")
        return _parse_newsletter_content_list(soup)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得電子報內容失敗: {e}")
