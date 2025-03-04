from datetime import datetime

from fastapi import APIRouter, Path, Query
from thefuzz import fuzz

from src.api.schemas.dining import (
    DiningBuilding,
    DiningBuildingName,
    DiningRestaurant,
    DiningScheduleKeyword,
    DiningScheduleName,
)
from src.utils import nthudata

router = APIRouter()
json_path = "dining.json"


def _is_restaurant_open(restaurant: DiningRestaurant, day: str) -> bool:
    """
    判斷餐廳在指定日期是否營業。

    分析餐廳資料中的 'note' 欄位，檢查是否包含表示特定日期休息的關鍵字。

    Args:
        restaurant (DiningRestaurant): 要檢查的餐廳資料。
        day (str): 要查詢的星期幾，使用英文小寫 (例如：'monday')。

    Returns:
        bool: 若餐廳在指定日期可能營業，則返回 True，否則返回 False。
    """
    note = restaurant.get("note", "").lower()
    for keyword in DiningScheduleKeyword.BREAK_KEYWORDS:
        for day_zh in DiningScheduleKeyword.DAY_EN_TO_ZH.get(day, []):
            if keyword in note and day_zh in note:
                return False  # 找到休息關鍵字，判斷為休息
    return True  # 未找到休息關鍵字，判斷為營業


@router.get("/", response_model=list[DiningBuilding])
async def get_dining_data(
    building_name: DiningBuildingName = Query(
        None, example="小吃部", description="餐廳建築名稱（可選）"
    )
) -> list[DiningBuilding]:
    """
    取得所有餐廳及服務性廠商資料。
    資料來源：[總務處經營管理組/餐廳及服務性廠商](https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw)
    """
    _commit_hash, dining_data = await nthudata.get(json_path)
    if building_name:
        return [
            building
            for building in dining_data
            if building["building"] == building_name
        ]
    return dining_data


@router.get(
    "/search",
    response_model=list[DiningRestaurant],
)
async def fuzzy_search_restaurants(
    query: str = Query(..., example="麵", description="餐廳模糊搜尋關鍵字")
) -> list[DiningRestaurant]:
    """
    使用餐廳名稱模糊搜尋餐廳資料。
    """
    _commit_hash, dining_data = await nthudata.get(json_path)
    results = []
    for building in dining_data:
        for restaurant in building.get("restaurants", []):
            similarity = fuzz.partial_ratio(query, restaurant["name"])
            if similarity >= 60:  # 相似度門檻值，可以調整
                restaurant["similarity_score"] = similarity  # 加入相似度分數方便排序
                results.append(restaurant)
    results.sort(
        key=lambda x: x.get("similarity_score", 0), reverse=True
    )  # 根據相似度排序
    return results


@router.get("/restaurants", response_model=list[DiningRestaurant])
async def get_all_restaurants(
    schedule: DiningScheduleName = Query(
        None, eexample="saturday", description="營業日"
    )
) -> list[DiningRestaurant]:
    """
    取得所有餐廳資料。
    - 可選輸入營業日篩選該營業日有營業的餐廳，預設為全部列出。
    """
    _commit_hash, dining_data = await nthudata.get(json_path)
    if schedule:
        if schedule == "today":
            schedule = datetime.now().strftime("%A").lower()
        return [
            restaurant
            for building in dining_data
            for restaurant in building.get("restaurants", [])
            if _is_restaurant_open(restaurant, schedule)
        ]
    return [
        restaurant
        for building in dining_data
        for restaurant in building.get("restaurants", [])
    ]
