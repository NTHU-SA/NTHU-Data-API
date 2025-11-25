"""Tests for domain services."""

import pytest

from data_api.domain.dining.enums import DiningScheduleKeyword
from data_api.domain.dining.services import is_restaurant_open


class TestDiningService:
    """Tests for dining service functions."""

    def test_is_restaurant_open_no_note(self):
        """Test restaurant with no note is open."""
        restaurant = {"name": "Test", "note": ""}
        assert is_restaurant_open(restaurant, "weekday") is True

    def test_is_restaurant_open_break_on_saturday(self):
        """Test restaurant with break on Saturday is closed."""
        restaurant = {"name": "Test", "note": "週六休息"}
        assert is_restaurant_open(restaurant, "saturday") is False

    def test_is_restaurant_open_break_different_day(self):
        """Test restaurant with break on different day is open."""
        restaurant = {"name": "Test", "note": "週日休息"}
        assert is_restaurant_open(restaurant, "saturday") is True

    def test_is_restaurant_open_weekend(self):
        """Test restaurant on weekend."""
        restaurant = {"name": "Test", "note": ""}
        assert is_restaurant_open(restaurant, "saturday") is True
        assert is_restaurant_open(restaurant, "sunday") is True

    def test_is_restaurant_open_weekday(self):
        """Test restaurant on weekday."""
        restaurant = {"name": "Test", "note": ""}
        assert is_restaurant_open(restaurant, "weekday") is True


class TestDiningScheduleKeyword:
    """Tests for DiningScheduleKeyword enum."""

    def test_break_keywords_exist(self):
        """Test break keywords are defined."""
        assert len(DiningScheduleKeyword.BREAK_KEYWORDS) > 0

    def test_day_mapping_exists(self):
        """Test day mapping is defined."""
        assert "weekday" in DiningScheduleKeyword.DAY_EN_TO_ZH
        assert "saturday" in DiningScheduleKeyword.DAY_EN_TO_ZH
        assert "sunday" in DiningScheduleKeyword.DAY_EN_TO_ZH
