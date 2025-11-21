"""
Legacy NTHU Data API module - maintained for backward compatibility.

This module is kept for backward compatibility with existing code.
New code should use src.utils.data_manager.NTHUDataManager instead.
"""

from typing import Optional

from .data_manager import NTHUDataManager

# Global data manager instance for backward compatibility
_data_manager: Optional[NTHUDataManager] = None


def _get_manager() -> NTHUDataManager:
    """Get or create the global data manager instance."""
    global _data_manager
    if _data_manager is None:
        _data_manager = NTHUDataManager()
    return _data_manager


async def get_file_details() -> list | None:
    """
    非同步取得 file_details.json 的資料，會自動檢查快取並更新。

    公開函式，用於獲取格式化後的 file_details.json 資料。此函式會先檢查快取，
    如果快取有效則直接返回快取資料，否則會非同步更新快取後再返回。

    Returns:
        list or None: 格式化後的檔案詳細資訊列表，如果獲取失敗則返回 None。
                      例如: [{'name': '/announcements.json', 'last_commit': '...', 'last_updated': '...'}, ...]
    """
    manager = _get_manager()
    return await manager.get_file_details()


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
        tuple[str, dict or list] or None: 指定 endpoint 資料的 commit hash，及其 JSON 資料（可以是字典或列表）。
                                          如果獲取失敗或 endpoint 不存在則返回 None。
    """
    manager = _get_manager()
    return await manager.get(endpoint_name)
