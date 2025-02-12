from enum import Enum

import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
from dateutil.parser import parse
from fastapi import HTTPException


class DataType(Enum):
    ALL = "all"
    RECRUITMENT = "01001"
    INTERNSHIP = "01002"
    EVENT = "01003"
    COURSE = "01004"
    ANNOUNCEMENT = "01005"


def process_timestamp(date: str) -> int | None:
    """
    將日期字串轉換為 Unix 時間戳記。

    如果日期字串可以被 dateutil 解析，則轉換為 Unix 時間戳記。
    如果解析失敗，則回傳 None。

    Args:
        date: 日期字串。

    Returns:
        Unix 時間戳記 (整數)，如果解析失敗則回傳 None。
    """
    if date is None:
        return None
    try:
        date_object = parse(date)
        timestamp = int(date_object.timestamp())
    except ValueError:
        timestamp = None
    return timestamp


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


def _parse_announcement_item(item: BeautifulSoup) -> dict:
    """
    解析單個公告項目 (<li> 元素) 的資訊。

    從 BeautifulSoup 的 <li> 元素中提取公告的標題、描述、連結、日期和 Unix 時間戳記。

    Args:
        item: BeautifulSoup 的 <li> 元素，代表一個公告項目。

    Returns:
        一個字典，包含解析後的公告資訊，鍵包括 'title', 'description', 'link', 'date', 'unix_timestamp'。
        如果某些資訊無法提取，則對應的值可能為 None。
    """
    title_element = item.select_one("h3")
    title = title_element.text if title_element else None

    description_element = item.select_one("div.col-md-9 span")
    description = description_element.text if description_element else None

    date = None
    date_month_element = item.select_one("div.g-color-text-light-v1 span.d-block")
    if date_month_element:
        date_month = date_month_element.text.replace("月", "").strip()
        date_year_element = item.select_one(
            "div.g-color-text-light-v1 span.d-block:nth-child(2)"
        )
        if date_year_element:
            date_year = date_year_element.text.replace("年", "").strip()
            date = f"{date_year}-{date_month}"

    unix_timestamp = process_timestamp(date)

    link_element = item.select_one("a")
    link = link_element.get("href") if link_element else None
    if link and link.startswith("news.aspx"):
        link = "https://goodjob-nthu.conf.asia/" + str(link)

    return {
        "title": title,
        "description": description,
        "link": link,
        "date": date,
        "unix_timestamp": unix_timestamp,
    }


@cached(cache=TTLCache(maxsize=2, ttl=60 * 60 * 4))
def get_announcements(data_type: DataType = DataType.ALL) -> list[dict]:
    """
    從 Goodjob 網站取得不同類型的公告資料。

    根據 `data_type` 參數，從 Goodjob 網站擷取對應類型的公告列表，
    並解析標題、描述、連結、日期和 Unix 時間戳記等資訊。

    Args:
        data_type: 資料類型 (DataType 列舉)，預設為 DataType.ALL (全部公告)。

    Returns:
        一個包含公告資料的列表，每個元素是一個字典，包含 'title', 'description', 'link', 'date', 'unix_timestamp' 等鍵。

    Raises:
        HTTPException: 當擷取或解析資料過程中發生錯誤時，會拋出 HTTPException。
    """
    # 全部公告:      https://goodjob-nthu.conf.asia/sys_news.aspx?nt=all
    # 徵才:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01001
    # 實習:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01002
    # 活動:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01003
    # 課程/證照/考試: https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01004
    # 宣導資料:       https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01005
    URL_PREFIX = "https://goodjob-nthu.conf.asia/sys_news.aspx?nt="
    url = URL_PREFIX + data_type.value
    try:
        webpage_content = _fetch_webpage_content(url)
        soup = BeautifulSoup(webpage_content, "html.parser")
        announcement_items = soup.select(
            "div.col-md-12 ul.list-unstyled li.u-block-hover"
        )
        if not announcement_items:
            return []  # 如果沒有公告項目，提前返回空列表

        announcements_data = []
        for item in announcement_items:
            parsed_item = _parse_announcement_item(item)
            announcements_data.append(parsed_item)

        return announcements_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"解析公告資料失敗: {e}, URL: {url}"
        )
