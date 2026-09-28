"""Offline regression tests for MCP search composition and validation."""

from copy import deepcopy
from datetime import datetime
from itertools import product

import pytest
from fastmcp import Client
from pydantic import ValidationError

from data_api.data.manager import nthudata
from data_api.domain.courses.models import CourseData
from data_api.domain.courses.services import courses_service
from data_api.domain.dining import services as dining_services
from data_api.mcp.server import mcp
from data_api.mcp.tools.courses import _search_courses
from data_api.mcp.tools.dining import _find_dining

FILTER_COMBINATIONS = list(product([False, True], repeat=3))


@pytest.fixture
def course_candidates(monkeypatch):
    candidates = [
        (
            flags,
            CourseData.from_dict(
                {
                    "id": f"{'11510ISS 509900' if flags[2] else 'OTHER'}-{index}",
                    "chinese_title": "服務科學導論" if flags[0] else "微積分",
                    "english_title": "Service Science" if flags[0] else "Calculus",
                    "teacher": "Teacher" if flags[1] else "Someone else",
                }
            ),
        )
        for index, flags in enumerate(FILTER_COMBINATIONS)
    ]
    monkeypatch.setattr(courses_service, "course_data", [course for _, course in candidates])
    return candidates


@pytest.mark.parametrize("selected", FILTER_COMBINATIONS)
@pytest.mark.parametrize("keyword", ["服務科學導論", "Service"])
async def test_course_filters_all_contribute(course_candidates, selected, keyword):
    filters = dict(
        zip(("keyword", "teacher", "course_id"), (keyword, "Teacher", "11510ISS 509900"))
    )
    arguments = {
        name: value for (name, value), enabled in zip(filters.items(), selected) if enabled
    }
    expected_ids = [
        course.id
        for flags, course in course_candidates
        if all(not enabled or matches for enabled, matches in zip(selected, flags))
    ]

    result = await _search_courses(**arguments)
    assert [course["id"] for course in result["courses"]] == expected_ids
    assert result["count"] == len(expected_ids)

    for name in arguments:
        impossible = {**arguments, name: "NTHU_REVIEW_NONEXISTENT_20260928"}
        assert await _search_courses(**impossible, limit=1) == {"count": 0, "courses": []}


@pytest.mark.parametrize(
    ("argument", "field"),
    [
        ("keyword", "chinese_title"),
        ("keyword", "english_title"),
        ("teacher", "teacher"),
        ("course_id", "id"),
    ],
)
@pytest.mark.parametrize(
    ("literal", "decoy"),
    [("C++", "CCC"), ("[AI]", "AI"), ("(", "ordinary"), (".", "ordinary"), ("\\", "ordinary")],
)
async def test_course_search_uses_literal_substrings(monkeypatch, argument, field, literal, decoy):
    match = CourseData.from_dict({"id": "match", field: f"prefix {literal} suffix"})
    other = CourseData.from_dict({"id": "decoy", field: decoy})
    monkeypatch.setattr(courses_service, "course_data", [other, match])

    result = await _search_courses(**{argument: literal})
    assert [course["id"] for course in result["courses"]] == [match.id]


@pytest.mark.parametrize("limit", [-100, 0, 101, 10**9])
async def test_course_limit_rejected_by_implementation(limit):
    with pytest.raises(ValidationError):
        await _search_courses(limit=limit)


async def test_course_limit_schema_and_protocol_validation(monkeypatch):
    monkeypatch.setattr(
        courses_service,
        "course_data",
        [CourseData.from_dict({"id": str(index)}) for index in range(105)],
    )
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool = next(tool for tool in tools if tool.name == "search_courses")
        limit_schema = tool.input_schema["properties"]["limit"]
        assert limit_schema["minimum"] == 1
        assert limit_schema["maximum"] == 100
        assert limit_schema["default"] == 20

        for limit in [-100, 0, 101, 10**9]:
            result = await client.call_tool(
                "search_courses", {"limit": limit}, raise_on_error=False
            )
            assert result.is_error

        for arguments, expected_count in [({}, 20), ({"limit": 1}, 1), ({"limit": 100}, 100)]:
            result = await client.call_tool("search_courses", arguments)
            assert result.data["count"] == expected_count
            assert len(result.data["courses"]) == expected_count


@pytest.fixture
def dining_candidates(monkeypatch):
    data = [
        {
            "building": building,
            "restaurants": [
                {
                    "name": f"{name}-{building_index}-{int(is_open)}",
                    "area": building,
                    "phone": "",
                    "schedule": "09:00-17:00",
                    "note": "" if is_open else "平日休息、週六休息、週日休息",
                }
                for name, is_open in product(["Pizza", "Sushi"], [False, True])
            ],
        }
        for building_index, building in enumerate(["小吃部", "水木生活中心"])
    ]
    original = deepcopy(data)
    calls = []

    async def fake_get(endpoint):
        assert endpoint == "dining.json"
        calls.append(endpoint)
        return "testhash", data

    class Saturday(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 9, 26)

    monkeypatch.setattr(nthudata, "get", fake_get)
    monkeypatch.setattr(dining_services, "datetime", Saturday)
    yield data, calls
    assert data == original


@pytest.mark.parametrize("selected", FILTER_COMBINATIONS)
@pytest.mark.parametrize("schedule", ["today", "weekday", "saturday", "sunday"])
async def test_dining_filters_all_contribute(dining_candidates, selected, schedule):
    data, calls = dining_candidates
    building, name, check_open = selected
    arguments = {}
    if building:
        arguments["building"] = "水木"
    if name:
        arguments["restaurant_name"] = "Sushi"
    if check_open:
        arguments["check_open"] = schedule

    result = await _find_dining(**arguments)
    if check_open:
        assert result["schedule"] == schedule
        restaurants = result["open_restaurants"]
    else:
        restaurants = [r for b in result["buildings"] for r in b["restaurants"]]

    expected_names = [
        r["name"]
        for b in data
        if not building or b["building"] == "水木生活中心"
        for r in b["restaurants"]
        if (not name or r["name"].startswith("Sushi")) and (not check_open or not r["note"])
    ]
    assert [r["name"] for r in restaurants] == expected_names
    assert calls == ["dining.json"]


async def test_dining_filters_before_limiting(monkeypatch):
    data = [
        {"building": "小吃部", "restaurants": [{"name": "Sushi"} for _ in range(25)]},
        {
            "building": "水木生活中心",
            "restaurants": (
                [{"name": "Pizza"} for _ in range(25)]
                + [{"name": "Sushi", "note": "平日休息、週六休息、週日休息"} for _ in range(25)]
                + [{"name": "Sushi match"}]
            ),
        },
    ]

    async def fake_get(endpoint):
        assert endpoint == "dining.json"
        return "testhash", data

    monkeypatch.setattr(nthudata, "get", fake_get)
    result = await _find_dining(building="水木", restaurant_name="Sushi", check_open="today")
    assert [r["name"] for r in result["open_restaurants"]] == ["Sushi match"]


@pytest.mark.parametrize("arguments", [{"building": "ZZZZZZ"}, {"restaurant_name": "ZZZZZZ"}])
async def test_dining_impossible_filter_with_open_status(dining_candidates, arguments):
    result = await _find_dining(**arguments, check_open="today")
    assert result == {"schedule": "today", "open_restaurants": []}
