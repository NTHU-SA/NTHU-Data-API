import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
from dateutil.parser import parse
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


def replace_numbers_in_url(url: str, new_number: str) -> str:
    """
    替換 URL 中頁碼的函式。

    這個函式接受一個 URL 和一個新的頁碼，並使用正則表達式將 URL 中的頁碼替換為新的頁碼。
    預期 URL 格式為 `-{number}.php`，例如 `-1.php`。

    Args:
        url: 原始 URL 字串。
        new_number: 新的頁碼字串。

    Returns:
        替換頁碼後的 URL 字串。
    """
    return re.sub(r"-\d+\.php", f"-{new_number}.php", url)


def process_date(mdate) -> str | None:
    """
    處理日期元素的函式。

    這個函式接受一個 BeautifulSoup 的元素，嘗試從中提取並清理日期字串。

    Args:
        mdate: BeautifulSoup 的元素，預期包含日期資訊。

    Returns:
        清理後的日期字串，如果輸入為 None 或無法提取日期，則返回 None。
    """
    if mdate is None:
        return None
    return mdate.text.strip()


def process_timestamp(date: str) -> int | None:
    """
    將日期字串轉換為 Unix 時間戳記。

    這個函式嘗試解析日期字串並將其轉換為 Unix 時間戳記。
    如果日期字串無法被解析，則返回 None。

    Args:
        date: 日期字串。

    Returns:
        Unix 時間戳記 (整數)，如果解析失敗則返回 None。
    """
    try:
        date_object = parse(date)
        return int(date_object.timestamp())
    except (ValueError, TypeError):
        return None


def process_link(url_dom, parsed_url) -> tuple[str | None, str | None]:
    """
    處理連結元素的函式。

    這個函式接受一個 BeautifulSoup 的連結元素和已解析的 URL 物件，
    提取連結的標題和 href 屬性，並將相對路徑的連結轉換為絕對路徑。

    Args:
        url_dom: BeautifulSoup 的連結元素。
        parsed_url: 使用 urllib.parse.urlparse 解析後的 URL 物件，用於解析相對路徑。

    Returns:
        一個元組，包含連結標題 (字串或 None) 和連結 href (字串或 None)。
    """
    if url_dom is not None:
        title = str(url_dom.get("title"))
        href = str(url_dom.get("href"))
        # 檢查 href 是否為相對路徑並轉換為絕對路徑
        if href.startswith("//"):
            href = f"{parsed_url.scheme}:{href}"
        elif href.startswith("/"):
            href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
    else:
        title = None
        href = None
    return title, href


@cached(cache=TTLCache(maxsize=128, ttl=60 * 30))
def get_announcement(
    url: str,
    start_page: int = 1,
    max_page: int = 1,
) -> list[dict]:
    """
    從指定 URL 獲取公告列表。

    這個函式從給定的 URL 開始，根據 `max_page` 參數，爬取多個頁面的公告資訊。
    它會處理分頁 URL，發送 HTTP 請求，解析 HTML 內容，並提取公告的標題、連結、日期和 Unix 時間戳記。

    Args:
        url: 公告列表頁面的基礎 URL。
        start_page: 起始爬取頁數，預設為 1。
        max_page: 最大爬取頁數，預設為 1。如果 `max_page` 大於 1，則會爬取多個分頁。

    Returns:
        一個包含公告資訊的列表，每個元素是一個字典
        包含 'title' (公告標題), 'link' (公告連結), 'date' (公告日期，格式為字串), 和 'unix_timestamp' (公告日期的 Unix 時間戳記)。

    Raises:
        HTTPException: 當 HTTP 請求失敗時，會拋出 HTTPException，包含錯誤碼和錯誤訊息。
    """
    page_list = [
        replace_numbers_in_url(url, str(i))
        for i in range(start_page, start_page + max_page)
    ]
    data = []
    try:
        for page_url in page_list:
            parsed_url = urlparse(page_url)
            webpage_content = _fetch_webpage_content(page_url)
            soup = BeautifulSoup(webpage_content, "html.parser")
            recruitments = soup.select("#pageptlist .listBS")
            for item in recruitments:
                mdate = item.select_one(".mdate")
                date = process_date(mdate)
                timestamp = process_timestamp(date)
                url_dom = item.select_one("a")
                title, href = process_link(url_dom, parsed_url)
                data.append(
                    {
                        "title": title,
                        "link": href,
                        "date": date,
                        "unix_timestamp": timestamp,
                    }
                )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"公告列表爬取失敗: {e}")
