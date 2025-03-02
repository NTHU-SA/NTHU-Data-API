import asyncio
import json
import time

import httpx

_cache = {}  # 記憶體快取，儲存資料與 commit hash
_file_details_url = "https://data.nthusa.tw/file_details.json"
_base_url = "https://data.nthusa.tw"
_file_details_cache = {
    "data": None,
    "last_updated": None,
    "expiry": 60 * 5,
}  # 快取 file_details.json, 預設 5 分鐘過期

# 建立 httpx AsyncClient session，在模組初始化時建立
_async_http_client = httpx.AsyncClient()


async def _fetch_json(url: str) -> dict | None:
    """
    私有函式：使用 httpx AsyncClient session 從 URL 非同步獲取 JSON 資料。

    Args:
        url (str): 要獲取的 JSON 資料的 URL。

    Returns:
        dict or None: 如果成功獲取並解析 JSON 資料，則返回字典；如果發生錯誤，則返回 None。
    """
    try:
        async with _async_http_client.stream(
            "GET", url
        ) as response:  # 使用 async with 確保資源釋放
            response.raise_for_status()  # 檢查 HTTP 錯誤
            data = await response.aread()  # 非同步讀取 response 內容
            return json.loads(data)
    except httpx.RequestError as e:
        print(f"Error fetching {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {url}: {e}")
        return None


async def _format_file_details(file_details: dict) -> list:
    """
    私有函式：格式化 file_details.json 的資料結構。

    原始的 file_details.json 結構較為巢狀，此函式將其轉換為扁平的列表結構，
    方便後續查詢和使用。

    Args:
        file_details (dict): 從 file_details.json 獲取的原始 JSON 資料。

    Returns:
        list: 格式化後的檔案詳細資訊列表，每個元素都是一個字典，包含 'name', 'last_commit', 'last_updated' 鍵。
            例如: [{'name': '/announcements.json', 'last_commit': '...', 'last_updated': '...'}, ...]
    """
    formatted_file_details = []
    if file_details.get("file_details"):
        file_details = file_details["file_details"]
        for section, files in file_details.items():
            if section == "/":
                section = ""
            for file_info in files:
                formatted_file_details.append(
                    {
                        "name": section + "/" + file_info["name"],
                        "last_commit": file_info["last_commit"],
                        "last_updated": file_info["last_updated"],
                    }
                )
    return formatted_file_details


async def _update_file_details():
    """
    私有函式：非同步更新 file_details.json 快取。

    此函式檢查 file_details.json 快取是否過期或不存在，如果需要更新，
    則會從遠端伺服器獲取最新的 file_details.json 資料並更新快取。
    """
    global _file_details_cache
    current_time = time.time()
    if (
        _file_details_cache["data"] is None
        or _file_details_cache["last_updated"] is None
        or (
            current_time - _file_details_cache["last_updated"]
            > _file_details_cache["expiry"]
        )
    ):
        print("Updating file_details.json...")
        file_details_data = await _fetch_json(
            _file_details_url
        )  # 使用 await 調用非同步函式
        if file_details_data:  # 確保成功獲取資料才進行格式化和更新
            formatted_file_details_data = await _format_file_details(file_details_data)
            _file_details_cache["data"] = formatted_file_details_data
            _file_details_cache["last_updated"] = current_time
            print("file_details.json updated.")
        else:
            print("Failed to update file_details.json.")
    else:
        print("Using cached file_details.json.")


async def get_file_details() -> list | None:
    """
    非同步取得 file_details.json 的資料，會自動檢查快取並更新。

    公開函式，用於獲取格式化後的 file_details.json 資料。此函式會先檢查快取，
    如果快取有效則直接返回快取資料，否則會非同步更新快取後再返回。

    Returns:
        list or None: 格式化後的檔案詳細資訊列表，如果獲取失敗則返回 None。
                      例如: [{'name': '/announcements.json', 'last_commit': '...', 'last_updated': '...'}, ...]
    """
    await _update_file_details()  # 使用 await 調用非同步函式
    return _file_details_cache["data"]


async def get(endpoint_name: str) -> tuple[str, dict | list] | None:
    """
    公開函式：非同步取得指定 endpoint 的 JSON 資料。
    會檢查快取和 commit hash 以判斷是否需要更新。

    此函式首先會獲取 file_details.json，然後根據 endpoint_name 找到對應的檔案資訊。
    接著檢查快取中是否有該 endpoint 的資料，並比對 commit hash。
    如果快取有效且 commit hash 一致，則返回快取資料；否則從遠端伺服器獲取最新資料並更新快取。

    Args:
        endpoint_name (str): endpoint 名稱，例如 "buses.json" 或 "dining/shops.json"。

    Returns:
        dict or list or None: 指定 endpoint 的 JSON 資料，可以是字典或列表，如果獲取失敗或 endpoint 不存在則返回 None。
    """
    if not endpoint_name.startswith("/"):
        endpoint_name = "/" + endpoint_name

    file_details_sections = await get_file_details()  # 使用 await 調用非同步函式
    if file_details_sections is None:
        print("Cannot fetch data because file_details.json is unavailable or invalid.")
        return None

    expected_commit_hash = None
    for file_info in file_details_sections:
        if file_info["name"] == endpoint_name:
            expected_commit_hash = file_info["last_commit"]
            break  # 找到對應檔案後跳出迴圈

    cached_data = _cache.get(endpoint_name)

    if cached_data and cached_data.get("commit_hash") == expected_commit_hash:
        print(f"Using cached data for '{endpoint_name}'.")
        return (cached_data["commit_hash"], cached_data["data"])
    else:
        print(f"Fetching fresh data for '{endpoint_name}'...")
        data_url = _base_url + endpoint_name
        fresh_data = await _fetch_json(data_url)  # 使用 await 調用非同步函式
        if fresh_data:
            _cache[endpoint_name] = {
                "data": fresh_data,
                "commit_hash": expected_commit_hash,
            }
            print(f"Data for '{endpoint_name}' updated in cache.")
            return (expected_commit_hash, fresh_data)
        else:
            print(f"Failed to fetch fresh data for '{endpoint_name}'.")
            # 如果獲取失敗，可以選擇返回舊的快取資料 (如果有的話)，或者返回 None
            return (
                (cached_data["commit_hash"], cached_data.get("data"))
                if cached_data
                else None
            )


# # 在模組載入時，先更新一次 file_details.json 快取 (非同步初始化需要用 asyncio.run 在事件迴圈中執行)
# async def _initialize_file_details():
#     await get_file_details()
# asyncio.get_event_loop().run_until_complete(_initialize_file_details())  # 改到各自 router 的 lifespan 執行


if __name__ == "__main__":

    async def main():  # 定義一個 async main 函式來包含所有的 await 操作
        file_details = await get_file_details()
        print(
            "File Details Sections (first 2 keys):",
            file_details[:2] if file_details else None,
        )

        endpoint1_data = await get("/buses.json")  # 測試根目錄檔案
        if endpoint1_data:
            print(endpoint1_data)

        endpoint2_data = await get(
            "buses/weekdayBusScheduleTowardMainCampus.json"
        )  # 測試子目錄檔案
        if endpoint2_data:
            print(endpoint2_data)

        endpoint1_data_cached = await get("buses.json")  # 再次請求，應該會使用快取
        if endpoint1_data_cached:
            print(endpoint1_data_cached)

        await asyncio.sleep(6 * 60)  # 非同步的 sleep

        endpoint1_data_after_wait = await get("buses.json")  # 等待快取過期後再次請求
        if endpoint1_data_after_wait:
            print(endpoint1_data_after_wait)

    async def run_main_with_client():  # 包裹 main 函式在 async with 裡面
        async with httpx.AsyncClient() as client:  # 使用 async with 建立並管理 AsyncClient
            global _async_http_client  # 宣告使用全域變數
            _async_http_client = (
                client  # 將 client 賦值給全域變數，這樣 _fetch_json 等函式才能使用
            )
            await main()

    asyncio.run(
        run_main_with_client()
    )  # 使用 asyncio.run() 執行 run_main_with_client 函式
