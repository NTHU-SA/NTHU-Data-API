import json
import re
from datetime import datetime, timedelta

import httpx
import xmltodict
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Path

from data_api.api.schemas.libraries import (
    LibraryLostAndFound,
    LibraryRssItem,
    LibraryRssType,
    LibrarySpace,
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

router = APIRouter()


@router.get(
    "/space",
    response_model=list[LibrarySpace],
    operation_id="getLibrarySpaceAvailability",
)
async def get_library_space_availability():
    """
    取得圖書館空間使用資訊。
    資料來源：[圖書館空間預約系統](https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx)
    """
    url = "https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx"
    try:
        async with httpx.AsyncClient(
            verify=False
        ) as client:  # 圖書館的 RSS 使用了特別的憑證(TWCA)
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            data = response.json()

            if data.get("resmsg") != "成功":
                raise HTTPException(status_code=404, detail="找不到空間資料")
            return data["rows"]
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, detail=f"擷取空間資料失敗: {e}"
        )
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"解析空間資料失敗: {e}")


@router.get(
    "/lost_and_found",
    response_model=list[LibraryLostAndFound],
    operation_id="getLibraryLostAndFoundItems",
)
async def get_library_lost_and_found_items():
    """
    取得圖書館失物招領資訊。
    資料來源：[圖書館失物招領系統](https://adage.lib.nthu.edu.tw/find)
    """
    date_end = datetime.now()
    date_start = date_end - timedelta(days=6 * 30)

    post_data = {
        "place": "0",
        "date_start": date_start.strftime("%Y-%m-%d"),
        "date_end": date_end.strftime("%Y-%m-%d"),
        "catalog": "ALL",
        "keyword": "",
        "SUMIT": "送出",
    }
    url = "https://adage.lib.nthu.edu.tw/find/search_it.php"

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, data=post_data, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            if not table:
                return []

            table_rows = table.find_all("tr")
            if not table_rows:
                return []

            # 提取表格標題
            table_title = [td.text.strip() for td in table_rows[0].find_all("td")]

            # 解析表格行
            rows_data = []
            for row in table_rows[1:]:
                cells = [
                    re.sub(r"\s+", " ", td.text.strip()) for td in row.find_all("td")
                ]
                if len(cells) == len(table_title):
                    rows_data.append(dict(zip(table_title, cells)))

            return rows_data
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, detail=f"擷取失物招領資料失敗: {e}"
        )
    except AttributeError:
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失物招領資料失敗: {e}")


@router.get(
    "/rss/{rss_type}",
    response_model=list[LibraryRssItem],
    operation_id="getLibraryRssData",
)
async def get_library_rss_data(
    rss_type: LibraryRssType = Path(
        ...,
        description="RSS 類型：最新消息(news)、電子資源(eresources)、展覽及活動(exhibit)、南大與人社分館(branches)",
    )
):
    """
    取得指定圖書館的 RSS 資料。
    資料來源：[圖書館官網展覽與活動](https://www.lib.nthu.edu.tw/events/index.html)
    """
    url = f"https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_{rss_type.value}.xml"
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()

            xml_string = response.text.replace("<br />", "")
            rss_dict = xmltodict.parse(xml_string)
            rss_data = rss_dict["rss"]["channel"]["item"]

            # 確保資料為列表
            if not isinstance(rss_data, list):
                rss_data = [rss_data]

            # 修正圖片 URL
            for item in rss_data:
                if item["image"]["url"].startswith("//"):
                    item["image"]["url"] = f"https:{item['image']['url']}"

            return rss_data
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, detail=f"擷取 RSS 資料失敗: {e}"
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="在回應中找不到 RSS 來源")
