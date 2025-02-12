import json
import re
from datetime import datetime, timedelta

import requests
import xmltodict
from bs4 import BeautifulSoup
from cachetools import TTLCache, cached
from dateutil.parser import parse
from fastapi import HTTPException

_default_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}


def process_timestamp(date: str) -> int | None:
    """
    解析日期字串並回傳 Unix 時間戳記。

    Args:
        date: 要解析的日期字串。

    Returns:
        Unix 時間戳記 (整數)，如果解析失敗則回傳 None。
    """
    try:
        date_object = parse(date)
        return int(date_object.timestamp())
    except (ValueError, TypeError):
        return None


@cached(cache=TTLCache(maxsize=4, ttl=60 * 60))
def get_rss_data(rss_type: str) -> list:
    """
    從清華大學圖書館公告欄擷取並解析 RSS 資料。

    Args:
        rss_type: RSS 類型 ('news', 'eresources', 'exhibit', 'branches')。

    Returns:
        包含 RSS 項目字典的列表。

    Raises:
        HTTPException: 如果找不到 RSS 來源 (404)。
        requests.exceptions.RequestException: 如果擷取 RSS 來源時發生問題。
    """
    # 最新消息 RSS:         https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_news.xml
    # 電子資源 RSS:         https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_eresources.xml
    # 展覽及活動 RSS:       https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_exhibit.xml
    # 南大與人社分館 RSS:   https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_branches.xml
    url = f"https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_{rss_type}.xml"
    try:
        response = requests.get(url, headers=_default_headers)
        response.raise_for_status()  # 針對錯誤的回應 (4xx 或 5xx) 拋出 HTTPError
        xml_string = response.text
        xml_string = xml_string.replace("<br />", "")
        rss_dict = xmltodict.parse(xml_string)
        rss_data = rss_dict["rss"]["channel"]["item"]
        if not isinstance(rss_data, list):
            rss_data = [rss_data]
        return rss_data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取 RSS 資料失敗: {e}")
    except KeyError:
        raise HTTPException(status_code=404, detail="在回應中找不到 RSS 來源")


def get_parsed_rss_data(rss_type: str) -> list:
    """
    擷取、解析並結構化 RSS 資料，以供 API 回應使用。

    Args:
        rss_type: RSS 類型 ('news', 'eresources', 'exhibit', 'branches')。

    Returns:
        包含字典的列表，每個字典包含解析後的 RSS 項目詳細資訊。
    """
    rss_data = get_rss_data(rss_type)
    data = []
    for item in rss_data:
        title = item["title"]
        link = item["link"]
        pubdate = item["pubDate"]
        description = item["description"]
        author = item["author"]
        image = item["image"]["url"]
        if image.startswith("//"):
            image = f"https:{image}"
        date = pubdate
        unix_timestamp = process_timestamp(date)
        data.append(
            {
                "title": title,
                "link": link,
                "date": pubdate,
                "description": description,
                "author": author,
                "image": image,
                "unix_timestamp": unix_timestamp,
            }
        )
    return data


@cached(cache=TTLCache(maxsize=1, ttl=60 * 60))
def get_number_of_goods() -> dict:
    """
    取得圖書館換證數量資訊。

    Returns:
        包含換證數量資訊的字典。

    Raises:
        HTTPException: 如果無法擷取資料 (500) 或解析資料。
        requests.exceptions.RequestException: 如果擷取資料時發生問題。
    """
    url = "https://adage.lib.nthu.edu.tw/goods/Public/number_of_goods_mix.js"
    headers = {
        "Referer": "https://www.lib.nthu.edu.tw/",
        **_default_headers,
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        text = response.text

        variables = re.findall(r"var\s+(\w+)\s*=\s*(\d+|'[^']*'|\"[^\"]*\");", text)
        data = {}
        for variable in variables:
            key, value = variable
            if value.startswith("'") or value.startswith('"'):
                value = value.strip("'\"")
            data[key] = value
        return data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取換證資料失敗: {e}")
    except Exception as e:  # 捕捉潛在的解析錯誤
        raise HTTPException(status_code=500, detail=f"解析換證資料失敗: {e}")


@cached(cache=TTLCache(maxsize=1, ttl=60 * 60))
def get_opening_hours(library_name) -> dict:
    """
    取得特定圖書館的開放時間。

    Args:
        library_name: 一個枚舉或物件，具有 'value' 屬性代表圖書館名稱。

    Returns:
        包含圖書館名稱和開放時間資訊的字典。

    Raises:
        HTTPException: 如果找不到開放時間 (404) 或時間格式無效 (500)。
        requests.exceptions.RequestException: 如果擷取資料時發生問題。
    """
    url = f"https://www.lib.nthu.edu.tw/bulletin/OpeningHours/{library_name.value}.js"
    try:
        response = requests.get(url, headers=_default_headers)
        response.raise_for_status()
        text = response.text

        match = re.search(
            r"var openhour ='(\d{4}-\d{2}-\d{2}\s+\([\w]+\))<br />(.*?)'", text
        )
        data = {"library": library_name.value}
        if match:
            data["date"] = match.group(1)
            opening_info = match.group(2)
            if opening_info == "不提供服務":
                data["start_time"] = ""
                data["end_time"] = ""
                data["message"] = "不提供服務"
            else:
                time_match = re.search(r"(\d{2}:\d{2})-(\d{2}:\d{2})", opening_info)
                if time_match:
                    data["start_time"] = time_match.group(1)
                    data["end_time"] = time_match.group(2)
                    data["message"] = "提供服務"
                else:
                    raise HTTPException(
                        status_code=500, detail="開放時間資料中時間格式無效"
                    )
        else:
            raise HTTPException(status_code=404, detail="找不到開放時間")
        return data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取開放時間資料失敗: {e}")


@cached(cache=TTLCache(maxsize=1, ttl=60))
def get_space_data() -> list:
    """
    取得圖書館即時空間使用資訊。

    Returns:
        包含字典的列表，每個字典代表一個空間及其使用狀態。

    Raises:
        HTTPException: 如果找不到空間資料 (404) 或 API 回應指示失敗。
        requests.exceptions.RequestException: 如果擷取資料時發生問題。
    """
    url = "https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx"
    try:
        response = requests.get(url, headers=_default_headers)
        response.raise_for_status()
        response_text = response.text

        data = json.loads(response_text)
        if data["resmsg"] != "成功":
            raise HTTPException(status_code=404, detail="找不到空間資料")
        return data["rows"]
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取空間資料失敗: {e}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="解析空間資料 JSON 失敗")


@cached(cache=TTLCache(maxsize=1, ttl=60 * 60))
def get_lost_and_found() -> list:
    """
    從圖書館網站取得失物招領物品。

    Returns:
        包含字典的列表，每個字典代表一個失物招領物品。

    Raises:
        HTTPException: 如果解析網站內容時發生問題。
        requests.exceptions.RequestException: 如果擷取網站時發生問題。
    """
    # 來源: https://adage.lib.nthu.edu.tw/find/
    date_end = datetime.now()
    date_start = date_end - timedelta(days=6 * 30)
    date_end = date_end.strftime("%Y-%m-%d")
    date_start = date_start.strftime("%Y-%m-%d")

    post_data = {
        "place": "0",
        "date_start": date_start,
        "date_end": date_end,
        "catalog": "ALL",
        "keyword": "",
        "SUMIT": "送出",
    }
    url = "https://adage.lib.nthu.edu.tw/find/search_it.php"

    try:
        response = requests.post(url, data=post_data, headers=_default_headers)
        response.raise_for_status()
        response_text = response.text
        soup = BeautifulSoup(response_text, "html.parser")

        table = soup.find("table")
        if not table:
            return []  # 如果找不到表格，回傳空列表，而不是拋出錯誤

        table_rows = table.find_all("tr")
        if not table_rows:
            return []  # 如果找不到列，回傳空列表

        table_title = table_rows[0].find_all("td")
        table_title = [x.text.strip() for x in table_title]

        def parse_table_row(table_row):
            text = table_row.find_all("td")
            return [re.sub(r"\s+", " ", x.text.strip()) for x in text]

        rows_data = [parse_table_row(row) for row in table_rows[1:]]
        rows_data = [
            dict(zip(table_title, row))
            for row in rows_data
            if len(row) == len(table_title)
        ]  # 確保列長度與標題長度相符
        return rows_data

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取失物招領資料失敗: {e}")
    except AttributeError:  # 處理 soup.find("table") 回傳 None 的情況
        return []  # 如果表格解析失敗，回傳空列表
    except Exception as e:  # 捕捉任何其他解析錯誤
        raise HTTPException(status_code=500, detail=f"解析失物招領資料失敗: {e}")
