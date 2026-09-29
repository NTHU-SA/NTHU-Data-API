"""Tests for domain services."""

from copy import deepcopy
from datetime import datetime

import pytest

from data_api.data.manager import nthudata
from data_api.domain.dining import services
from data_api.domain.dining.enums import DiningScheduleKeyword
from data_api.domain.dining.services import is_restaurant_open


class TestDiningService:
    """Tests for dining service functions."""

    async def test_is_restaurant_open_no_note(self):
        """Test restaurant with no note is open."""
        restaurant = {"name": "Test", "note": ""}
        assert is_restaurant_open(restaurant, "weekday") is True

    async def test_is_restaurant_open_break_on_saturday(self):
        """Test restaurant with break on Saturday is closed."""
        restaurant = {"name": "Test", "note": "週六休息"}
        assert is_restaurant_open(restaurant, "saturday") is False

    async def test_is_restaurant_open_break_different_day(self):
        """Test restaurant with break on different day is open."""
        restaurant = {"name": "Test", "note": "週日休息"}
        assert is_restaurant_open(restaurant, "saturday") is True

    async def test_is_restaurant_open_weekend(self):
        """Test restaurant on weekend."""
        restaurant = {"name": "Test", "note": ""}
        assert is_restaurant_open(restaurant, "saturday") is True
        assert is_restaurant_open(restaurant, "sunday") is True

    async def test_is_restaurant_open_weekday(self):
        """Test restaurant on weekday."""
        restaurant = {"name": "Test", "note": ""}
        assert is_restaurant_open(restaurant, "weekday") is True


class TestDiningScheduleKeyword:
    """Tests for DiningScheduleKeyword enum."""

    async def test_break_keywords_exist(self):
        """Test break keywords are defined."""
        assert len(DiningScheduleKeyword.BREAK_KEYWORDS) > 0

    async def test_day_mapping_exists(self):
        """Test day mapping is defined."""
        assert "weekday" in DiningScheduleKeyword.DAY_EN_TO_ZH
        assert "saturday" in DiningScheduleKeyword.DAY_EN_TO_ZH
        assert "sunday" in DiningScheduleKeyword.DAY_EN_TO_ZH


@pytest.mark.parametrize(
    "instant,closed_day",
    [
        ("2026-09-25T15:59:59+00:00", "weekday"),
        ("2026-09-25T16:00:00+00:00", "saturday"),
        ("2026-09-26T15:59:59+00:00", "saturday"),
        ("2026-09-26T16:00:00+00:00", "sunday"),
        ("2026-09-27T15:59:59+00:00", "sunday"),
        ("2026-09-27T16:00:00+00:00", "weekday"),
    ],
)
@pytest.mark.parametrize(
    "method", ["get_dining_data", "fuzzy_search_dining_data", "get_open_restaurants"]
)
async def test_today_uses_taiwan_date(monkeypatch, instant, closed_day, method):
    restaurants = [
        {"name": "weekday", "note": "平日休息"},
        {"name": "saturday", "note": "週六休息"},
        {"name": "sunday", "note": "週日休息"},
    ]
    data = [{"building": "Test", "metadata": "preserved", "restaurants": restaurants}]
    original = deepcopy(data)
    calls = []
    now = datetime.fromisoformat(instant)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert str(tz) == "Asia/Taipei"
            return now.astimezone(tz)

    async def fake_get(endpoint):
        calls.append(endpoint)
        return "hash", data

    monkeypatch.setattr(services, "datetime", FrozenDatetime)
    monkeypatch.setattr(nthudata, "get", fake_get)
    version, result = await getattr(services.dining_service, method)(schedule="today")
    excluded = {
        "weekday": {"weekday"},
        "saturday": {"saturday"},
        # The legacy note heuristic also treats "平日休息" as a Sunday closure.
        "sunday": {"weekday", "sunday"},
    }[closed_day]
    expected = [r for r in restaurants if r["name"] not in excluded]
    assert result == (
        expected if method == "get_open_restaurants" else [{**data[0], "restaurants": expected}]
    )
    assert version == "hash"
    assert calls == ["dining.json"]
    assert data == original
