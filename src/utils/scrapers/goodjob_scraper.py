from enum import Enum

import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
from dateutil.parser import parse


class DataType(Enum):
    ALL = "all"
    RECRUITMENT = "01001"
    INTERNSHIP = "01002"
    EVENT = "01003"
    COURSE = "01004"
    ANNOUNCEMENT = "01005"


def process_timestamp(date):
    if date is None:
        return None
    try:
        date = parse(date)
        timestamp = int(date.timestamp())
    except ValueError:
        # 如果日期不能被解析，返回 None
        timestamp = None
    return timestamp


@cached(cache=TTLCache(maxsize=2, ttl=60 * 60 * 4))
def get_announcements(data_type: DataType = DataType.ALL) -> list:
    """
    從 Goodjob 取得活動資料。
    Args:
        data_type (str): 資料類型。
    Returns:
        list: 活動資料。
    """
    # 全部公告:      https://goodjob-nthu.conf.asia/sys_news.aspx?nt=all
    # 徵才:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01001
    # 實習:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01002
    # 活動:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01003
    # 課程/證照/考試: https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01004
    # 宣導資料:       https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01005
    URL_PREFIX = "https://goodjob-nthu.conf.asia/sys_news.aspx?nt="
    response = requests.get(URL_PREFIX + data_type.value).text
    soup = BeautifulSoup(response, "html.parser")
    items = soup.select("div.col-md-12 ul.list-unstyled li.u-block-hover")
    data = []
    for item in items:
        # 取得標題
        title = item.select_one("h3")
        if title is not None:
            title = title.text
        # 取得描述
        description = item.select_one("div.col-md-9 span")
        if description is not None:
            description = description.text
        # 取得日期
        date = None
        date_month = item.select_one("div.g-color-text-light-v1 span.d-block")
        if date_month is not None:
            date_month = date_month.text.replace("月", "")
            date_year = item.select_one(
                "div.g-color-text-light-v1 span.d-block:nth-child(2)"
            )
            if date_year is not None:
                date_year = date_year.text.replace("年", "")
                date = f"{date_year}-{date_month}"
        unix_timestamp = process_timestamp(date)
        # 取得網址
        link = item.select_one("a")
        if link is not None:
            link = link.get("href")
            if link.startswith("news.aspx"):
                link = "https://goodjob-nthu.conf.asia/" + str(link)
        data.append(
            {
                "title": title,
                "description": description,
                "link": link,
                "date": date,
                "unix_timestamp": unix_timestamp,
            }
        )

    return data
