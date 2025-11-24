"""Dining domain enums."""

from enum import Enum


class DiningBuildingName(str, Enum):
    """Dining building names."""

    小吃部 = "小吃部"
    水木生活中心 = "水木生活中心"
    風雲樓 = "風雲樓"
    綜合教學大樓_南大校區 = "綜合教學大樓(南大校區)"
    其他餐廳 = "其他餐廳"


class DiningScheduleName(str, Enum):
    """Schedule names for dining queries."""

    today = "today"
    weekday = "weekday"
    saturday = "saturday"
    sunday = "sunday"


class DiningScheduleKeyword:
    """Keywords for parsing dining schedules."""

    DAY_EN_TO_ZH = {
        "weekday": ["平日"],
        "saturday": ["週六", "星期六", "禮拜六", "六"],
        "sunday": ["週日", "星期日", "禮拜日", "日"],
    }
    BREAK_KEYWORDS = ["暫停營業", "休息", "休業", "休"]
