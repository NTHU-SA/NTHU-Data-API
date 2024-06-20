import json
import re
from datetime import datetime, timedelta

import xmltodict
from bs4 import BeautifulSoup
from dateutil.parser import parse
from fastapi import HTTPException

from src.utils import cached_requests


def process_timestamp(date):
    try:
        date = parse(date)
        timestamp = int(date.timestamp())
    except (ValueError, TypeError):
        # 如果日期不能被解析，返回 None
        timestamp = None
    return timestamp


def get_rss_data(rss_type: str) -> list:
    """
    Args:
        rss_type (str): RSS 類型，可選值: news（最新消息）、eresources（電子資源）、exhibit（展覽及活動）、branches（南大與人社分館）
    """
    # 最新消息 RSS:         https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_news.xml
    # 電子資源 RSS:         https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_eresources.xml
    # 展覽及活動 RSS:       https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_exhibit.xml
    # 南大與人社分館 RSS:   https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_branches.xml
    url = f"https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_{rss_type}.xml"
    xml_string, using_cache = cached_requests.get(url, update=True, auto_headers=True)
    xml_string = xml_string.replace("<br />", "")
    rss_dict = xmltodict.parse(xml_string)
    rss_data = rss_dict["rss"]["channel"]["item"]
    return rss_data


def get_parsed_rss_data(rss_type: str) -> list:
    rss_data = get_rss_data(rss_type)
    data = []
    for item in rss_data:
        title = item["title"]
        link = item["link"]
        pubDate = item["pubDate"]
        description = item["description"]
        author = item["author"]
        image = item["image"]["url"]
        if image.startswith("//"):
            image = f"https:{image}"
        date = pubDate
        unix_timestamp = process_timestamp(date)
        data.append(
            {
                "title": title,
                "link": link,
                "date": pubDate,
                "description": description,
                "author": author,
                "image": image,
                "unix_timestamp": unix_timestamp,
            }
        )
    return data


def get_number_of_goods() -> dict:
    """
    取得總圖換證數量資訊。
    """
    url = "https://adage.lib.nthu.edu.tw/goods/Public/number_of_goods_mix.js"
    text, using_cache = cached_requests.get(url, update=True, auto_headers=True)
    # 使用正規表達式從 text 中提取變量和值
    variables = re.findall(r'var\s+(\w+)\s*=\s*(\d+|"[^"]*");', text)
    # 將變量和值存儲在字典中
    data = {}
    for variable in variables:
        key, value = variable
        if not value.isdigit():
            value = value.strip('"')
        data[key] = value
    return data


def get_opening_hours(libaray_name) -> dict:
    """
    取得指定圖書館的開放時間。
    """
    url = f"https://www.lib.nthu.edu.tw/bulletin/OpeningHours/{libaray_name.value}.js"
    text, using_cache = cached_requests.get(url, update=True, auto_headers=True)
    # 使用正規表達式從 text 中提取日期和時間
    match = re.search(
        r"(\d{4}-\d{2}-\d{2}\s+\([\w]+\))<br />(\d{2}:\d{2})-(\d{2}:\d{2})", text
    )
    data = {"library": libaray_name.value}
    if match:
        data["date"] = match.group(1)
        data["start_time"] = match.group(2)
        data["end_time"] = match.group(3)
    else:
        raise HTTPException(404, "Not found")
    return data


def get_space_data() -> list:
    """
    取得空間使用資訊。
    """
    # 來源： https://libsms.lib.nthu.edu.tw/build/
    url = "https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx"
    response, using_cache = cached_requests.get(url, update=True, auto_headers=True)
    data = json.loads(response)
    if data["resmsg"] != "成功":
        raise HTTPException(404, "Not found")
    else:
        return data["rows"]


def get_lost_and_found() -> list:
    """
    取得失物招領資訊。
    """
    # 來源: https://adage.lib.nthu.edu.tw/find/
    # 獲取日期
    date_end = datetime.now()
    date_start = date_end - timedelta(days=6 * 30)
    date_end = date_end.strftime("%Y-%m-%d")
    date_start = date_start.strftime("%Y-%m-%d")
    # 發送 POST 請求
    response = cached_requests.post(
        "https://adage.lib.nthu.edu.tw/find/search_it.php",
        data={
            "place": "0",
            "date_start": date_start,
            "date_end": date_end,
            "catalog": "ALL",
            "keyword": "",
            "SUMIT": "送出",
        },
    )
    # 找到表格
    soup = BeautifulSoup(response, "html.parser")
    table = soup.find("table")
    # 初始化一個列表來存儲所有行的數據
    rows_data = []
    table_rows = table.find_all("tr")
    # 處理表頭
    table_title = table_rows[0].find_all("td")
    # 將表頭轉成列表
    table_title = [x.text.strip() for x in table_title]

    # 處理表格每一行的數據
    def parse_table_row(table_row):
        text = table_row.find_all("td")
        return [re.sub(r"\s+", " ", x.text.strip()) for x in text]

    # 遍歷表格的每一行
    for row in table_rows[1:]:
        rows_data.append(parse_table_row(row))

    # 將表頭和表格數據合併
    rows_data = [dict(zip(table_title, row)) for row in rows_data]
    return rows_data
