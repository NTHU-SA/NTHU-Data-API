import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached


@cached(cache=TTLCache(maxsize=2, ttl=60 * 60 * 4))
def get_announcements(data_type: str) -> list:
    """
    從 Goodjob 取得活動資料。
    Args:
        data_type (str): 資料類型。
    """
    # 全部公告:      https://goodjob-nthu.conf.asia/sys_news.aspx?nt=all
    # 徵才:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01001
    # 實習:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01002
    # 活動:          https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01003
    # 課程/證照/考試: https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01004
    # 宣導資料:       https://goodjob-nthu.conf.asia/sys_news.aspx?nt=01005
    URL_PREFIX = "https://goodjob-nthu.conf.asia/sys_news.aspx?nt="
    response = requests.get(URL_PREFIX + data_type).text
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
        data.append(
            {
                "title": title,
                "description": description,
                "date": date,
            }
        )

    return data
