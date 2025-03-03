import json
import re
from datetime import datetime, timedelta

import requests

# TODO: 這邊之後可以考慮改寫成 async，避免跟之前一樣有機率等很久甚至卡死
import xmltodict
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Path

from src.api.schemas import libraries

_default_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

router = APIRouter()


@router.get("/space", response_model=list[libraries.LibrarySpace])
def get_library_space_data():
    """
    取得空間使用資訊。
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


@router.get("/lost_and_found", response_model=list[libraries.LibraryLostAndFound])
def get_library_lost_and_found():
    """
    取得失物招領資訊。
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


@router.get("/rss/{rss_type}", response_model=list[libraries.RssItem])
def get_library_rss_data(
    rss_type: libraries.LibraryRssType = Path(
        ...,
        description="RSS 類型：最新消息(news)、電子資源(eresources)、展覽及活動(exhibit)、南大與人社分館(branches)",
    )
):
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
    url = f"https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_{rss_type.value}.xml"
    try:
        response = requests.get(url, headers=_default_headers)
        response.raise_for_status()  # 針對錯誤的回應 (4xx 或 5xx) 拋出 HTTPError
        xml_string = response.text
        xml_string = xml_string.replace("<br />", "")
        rss_dict = xmltodict.parse(xml_string)
        rss_data = rss_dict["rss"]["channel"]["item"]
        if not isinstance(rss_data, list):
            rss_data = [rss_data]
        for item in rss_data:
            if item["image"]["url"].startswith("//"):
                item["image"]["url"] = f"https:{item['image']['url']}"

        return rss_data
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取 RSS 資料失敗: {e}")
    except KeyError:
        raise HTTPException(status_code=404, detail="在回應中找不到 RSS 來源")


@router.get("/openinghours/{library_name}", response_model=dict)
def get_library_opening_hours(
    library_name: libraries.LibraryName = Path(
        ...,
        description="圖書館代號：總圖(mainlib)、人社圖書館(hslib)、南大圖書館(nandalib)、夜讀區(mainlib_moonlight_area)",
    )
):
    """
    取得指定圖書館的開放時間。
    """
    url = f"https://www.lib.nthu.edu.tw/bulletin/OpeningHours/{library_name.value}.json"
    try:
        response = requests.get(url, headers=_default_headers)
        response.raise_for_status()
        data_json = response.json()  # parse json
        return data_json
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取開放時間資料失敗: {e}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="解析開放時間資料 JSON 失敗")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析開放時間資料失敗: {e}")


@router.get("/goods", response_model=libraries.LibraryNumberOfGoods)
def get_library_number_of_goods():
    """
    取得總圖換證數量資訊。
    """
    url = "https://adage.lib.nthu.edu.tw/goods/Public/number_of_goods_mix.json"
    headers = {
        "Referer": "https://www.lib.nthu.edu.tw/",
        **_default_headers,
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data_json = response.json()  # parse json
        return data_json
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"擷取換證資料失敗: {e}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="解析換證資料 JSON 失敗")
    except Exception as e:  # 捕捉潛在的解析錯誤
        raise HTTPException(status_code=500, detail=f"解析換證資料失敗: {e}")
