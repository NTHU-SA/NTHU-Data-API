from datetime import datetime
from typing import List

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


@router.get("/", response_model=List[DiningBuilding])
async def get_all_dining_data() -> List[DiningBuilding]:
    """
    取得所有餐廳資料。
    https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw
    """
    _commit_hash, dining_data = await nthudata.get(json_path)
    return dining_data


@router.get("/buildings/{building_name}", response_model=DiningBuilding)
async def get_dining_data_in_buildings(
    building_name: DiningBuildingName = Path(
        ..., example="小吃部", description="建築名稱"
    )
) -> DiningBuilding:
    """
    使用建築名稱取得指定建築的餐廳資料。
    """
    _commit_hash, dining_data = await nthudata.get(json_path)
    return next(
        (building for building in dining_data if building["building"] == building_name),
        {},
    )


@router.get("/schedules/{day_of_week}", response_model=List[DiningRestaurant])
async def get_schedule_by_day_of_week(
    day_of_week: DiningScheduleName = Path(
        ..., example="saturday", description="營業日"
    )
) -> List[DiningRestaurant]:
    """
    取得所有該營業日的餐廳資訊。
    """
    _commit_hash, dining_data = await nthudata.get(json_path)
    if day_of_week == "today":
        day_of_week = datetime.now().strftime("%A").lower()
    return [
        restaurant
        for building in dining_data
        for restaurant in building.get("restaurants", [])
        if _is_restaurant_open(restaurant, day_of_week)
    ]


@router.get(
    "/search",
    response_model=List[DiningRestaurant],
)
async def fuzzy_search_restaurant_by_name(
    restaurant_name: str = Query(..., example="麵", description="餐廳模糊搜尋關鍵字")
) -> List[DiningRestaurant]:
    """
    使用餐廳名稱模糊搜尋餐廳資料。
    """
    _commit_hash, dining_data = await nthudata.get(json_path)
    results = []
    for building in dining_data:
        for restaurant in building.get("restaurants", []):
            similarity = fuzz.partial_ratio(restaurant_name, restaurant["name"])
            if similarity >= 60:  # 相似度門檻值，可以調整
                restaurant["similarity_score"] = similarity  # 加入相似度分數方便排序
                results.append(restaurant)
    results.sort(
        key=lambda x: x.get("similarity_score", 0), reverse=True
    )  # 根據相似度排序
    return results
