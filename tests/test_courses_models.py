"""Tests for course domain models."""

import pytest

from data_api.domain.courses.models import Condition, Conditions, CourseData


class TestCourseData:
    """Tests for CourseData model."""

    def test_from_dict_with_chinese_keys(self):
        """Test creating CourseData from dict with Chinese keys."""
        data = {
            "科號": "MATH1001",
            "課程中文名稱": "微積分",
            "課程英文名稱": "Calculus",
            "學分數": "3",
            "人限": "50",
            "新生保留人數": "10",
            "通識對象": "全校",
            "通識類別": "自然",
            "授課語言": "中文",
            "備註": "無",
            "停開註記": "",
            "教室與上課時間": "M3M4",
            "授課教師": "張三",
            "擋修說明": "",
            "課程限制說明": "",
            "第一二專長對應": "",
            "學分學程對應": "",
            "不可加簽說明": "",
            "必選修說明": "必修",
        }
        course = CourseData.from_dict(data)
        assert course.id == "MATH1001"
        assert course.chinese_title == "微積分"
        assert course.english_title == "Calculus"
        assert course.credit == "3"

    def test_from_dict_with_english_keys(self):
        """Test creating CourseData from dict with English keys."""
        data = {
            "id": "CS1001",
            "chinese_title": "程式設計",
            "english_title": "Programming",
            "credit": "3",
            "size_limit": "60",
            "freshman_reservation": "15",
            "object": "",
            "ge_type": "",
            "language": "中文",
            "note": "",
            "suspend": "",
            "class_room_and_time": "T2T3",
            "teacher": "李四",
            "prerequisite": "",
            "limit_note": "",
            "expertise": "",
            "program": "",
            "no_extra_selection": "",
            "required_optional_note": "",
        }
        course = CourseData.from_dict(data)
        assert course.id == "CS1001"
        assert course.chinese_title == "程式設計"

    def test_from_dict_missing_fields(self):
        """Test creating CourseData with missing fields defaults to empty string."""
        data = {"科號": "TEST001"}
        course = CourseData.from_dict(data)
        assert course.id == "TEST001"
        assert course.chinese_title == ""
        assert course.credit == ""

    def test_repr(self):
        """Test CourseData string representation."""
        data = {"科號": "TEST001", "課程中文名稱": "測試課程"}
        course = CourseData.from_dict(data)
        repr_str = repr(course)
        assert "TEST001" in repr_str


class TestCondition:
    """Tests for Condition model."""

    def test_condition_exact_match(self):
        """Test exact match condition."""
        course = CourseData.from_dict({"科號": "MATH1001", "課程中文名稱": "微積分"})
        cond = Condition(row_field="id", matcher="MATH1001", regex_match=False)
        assert cond.check(course) is True

    def test_condition_exact_match_fail(self):
        """Test exact match condition fails for non-matching."""
        course = CourseData.from_dict({"科號": "MATH1001", "課程中文名稱": "微積分"})
        cond = Condition(row_field="id", matcher="CS1001", regex_match=False)
        assert cond.check(course) is False

    def test_condition_regex_match(self):
        """Test regex match condition."""
        course = CourseData.from_dict({"科號": "MATH1001", "課程中文名稱": "微積分"})
        cond = Condition(row_field="id", matcher="MATH", regex_match=True)
        assert cond.check(course) is True

    def test_condition_regex_match_fail(self):
        """Test regex match condition fails for non-matching."""
        course = CourseData.from_dict({"科號": "MATH1001", "課程中文名稱": "微積分"})
        cond = Condition(row_field="id", matcher="CS", regex_match=True)
        assert cond.check(course) is False

    def test_condition_field_name_lowercase(self):
        """Test field name is converted to lowercase."""
        course = CourseData.from_dict({"科號": "MATH1001"})
        cond = Condition(row_field="ID", matcher="MATH1001", regex_match=False)
        assert cond.row_field == "id"


class TestConditions:
    """Tests for Conditions model."""

    def test_conditions_single(self):
        """Test single condition."""
        course = CourseData.from_dict({"科號": "MATH1001", "課程中文名稱": "微積分"})
        conds = Conditions(row_field="id", matcher="MATH", regex_match=True)
        assert conds.accept(course) is True

    def test_conditions_and(self):
        """Test AND combination of conditions."""
        course = CourseData.from_dict(
            {"科號": "MATH1001", "課程中文名稱": "微積分", "學分數": "3"}
        )
        cond1 = Conditions(row_field="id", matcher="MATH", regex_match=True)
        cond2 = Conditions(row_field="credit", matcher="3", regex_match=False)
        combined = cond1 & cond2
        assert combined.accept(course) is True

    def test_conditions_or(self):
        """Test OR combination of conditions."""
        course = CourseData.from_dict({"科號": "MATH1001", "課程中文名稱": "微積分"})
        cond1 = Conditions(row_field="id", matcher="CS", regex_match=True)
        cond2 = Conditions(row_field="id", matcher="MATH", regex_match=True)
        combined = cond1 | cond2
        assert combined.accept(course) is True

    def test_conditions_complex(self):
        """Test complex condition tree."""
        course = CourseData.from_dict(
            {"科號": "MATH1001", "課程中文名稱": "微積分", "學分數": "3"}
        )
        cond1 = Conditions(row_field="id", matcher="MATH", regex_match=True)
        cond2 = Conditions(row_field="credit", matcher="3", regex_match=False)
        cond3 = Conditions(row_field="id", matcher="CS", regex_match=True)
        combined = (cond1 & cond2) | cond3
        assert combined.accept(course) is True

    def test_conditions_from_list(self):
        """Test conditions from list_build_target."""
        course = CourseData.from_dict({"科號": "MATH1001"})
        conds = Conditions(
            list_build_target=[
                {"row_field": "id", "matcher": "MATH", "regex_match": True},
                "and",
                True,
            ]
        )
        assert conds.accept(course) is True

    def test_conditions_empty_list(self):
        """Test conditions with empty list returns True."""
        course = CourseData.from_dict({"科號": "MATH1001"})
        conds = Conditions(list_build_target=[])
        assert conds.accept(course) is True

    def test_conditions_no_args_raises(self):
        """Test that missing required args raises ValueError."""
        with pytest.raises(ValueError):
            Conditions()

    def test_conditions_unknown_operator_raises(self):
        """Test that unknown operator raises ValueError."""
        course = CourseData.from_dict({"科號": "MATH1001"})
        conds = Conditions(
            list_build_target=[
                {"row_field": "id", "matcher": "MATH", "regex_match": True},
                "xor",
                {"row_field": "id", "matcher": "CS", "regex_match": True},
            ]
        )
        with pytest.raises(ValueError, match="Unknown operator"):
            conds.accept(course)

    def test_conditions_invalid_item_type_raises(self):
        """Test that invalid condition item type raises TypeError."""
        course = CourseData.from_dict({"科號": "MATH1001"})
        conds = Conditions(list_build_target=["invalid_string", "and", True])
        with pytest.raises(TypeError, match="Cannot handle condition item"):
            conds.accept(course)
