from bs4 import BeautifulSoup
from src.utils import cached_request


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
    url_prefix = "https://goodjob-nthu.conf.asia/sys_news.aspx?nt="
    response = cached_request.get(url_prefix + data_type)
    soup = BeautifulSoup(response, "html.parser")
    items = soup.select("div.col-md-12 ul.list-unstyled li.u-block-hover")

    data = []
    for item in items:
        title = item.select_one("h3").text
        date_month = item.select_one("div.g-color-text-light-v1 span.d-block").text
        date_month = date_month.replace("月", "")
        date_year = item.select_one(
            "div.g-color-text-light-v1 span.d-block:nth-child(2)"
        ).text
        description = item.select_one("div.col-md-9 span").text
        data.append(
            {
                "title": title,
                "description": description,
                "date": f"{date_year}-{date_month}",
            }
        )

    return data
