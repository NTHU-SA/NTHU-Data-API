"""Offline regression tests for MCP search composition and validation."""

from copy import deepcopy
from datetime import datetime
from itertools import product

import pytest
from conftest import make_course, set_courses
from fastmcp import Client
from pydantic import ValidationError

from data_api.core.exceptions import DataNotAvailableException
from data_api.data.manager import nthudata
from data_api.domain.dining import services as dining_services
from data_api.mcp.server import mcp
from data_api.mcp.tools.courses import _search_courses
from data_api.mcp.tools.dining import _find_dining
from data_api.runtime import get_runtime

FILTER_COMBINATIONS = list(product([False, True], repeat=3))


@pytest.fixture(autouse=True)
def fixed_course_refresh(monkeypatch):
    set_courses(monkeypatch, [])


@pytest.fixture
def course_candidates(monkeypatch):
    candidates = [
        (
            flags,
            make_course(
                {
                    "id": f"{'11510ISS 509900' if flags[2] else '11510OTHER'}-{index}",
                    "chinese_title": "服務科學導論" if flags[0] else "微積分",
                    "english_title": "Service Science" if flags[0] else "Calculus",
                    "lecturers": [{"label": "Teacher" if flags[1] else "Someone else"}],
                }
            ),
        )
        for index, flags in enumerate(FILTER_COMBINATIONS)
    ]
    set_courses(monkeypatch, [course for _, course in candidates])
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
    value, other_value = f"prefix {literal} suffix", decoy
    if field == "teacher":
        field, value, other_value = "lecturers", [{"label": value}], [{"label": other_value}]
    if field == "id":
        match = make_course(id=f"11510prefix {literal} suffix")
        other = make_course(id=f"11510{decoy}")
    else:
        match = make_course({"id": "11510match", field: value})
        other = make_course({"id": "11510decoy", field: other_value})
    set_courses(monkeypatch, [other, match])

    result = await _search_courses(**{argument: literal})
    assert [course["id"] for course in result["courses"]] == [match.id]


@pytest.mark.parametrize("limit", [-100, 0, 101, 10**9])
async def test_course_limit_rejected_by_implementation(limit):
    with pytest.raises(ValidationError):
        await _search_courses(limit=limit)


async def test_course_limit_schema_and_protocol_validation(monkeypatch):
    set_courses(monkeypatch, [make_course(id=f"11510{index}") for index in range(105)])
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
        def now(cls, tz=None):
            return cls(2026, 9, 26, tzinfo=tz)

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
    assert set(result) == {"buildings"}
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
    assert [b["building"] for b in result["buildings"]] == ["水木生活中心"]
    assert [r["name"] for r in result["buildings"][0]["restaurants"]] == ["Sushi match"]


@pytest.mark.parametrize("arguments", [{"building": "ZZZZZZ"}, {"restaurant_name": "ZZZZZZ"}])
async def test_dining_impossible_filter_with_open_status(dining_candidates, arguments):
    result = await _find_dining(**arguments, check_open="today")
    assert result == {"buildings": []}


@pytest.mark.parametrize("check_open", [None, "today", "weekday", "saturday", "sunday"])
@pytest.mark.parametrize(
    ("building", "expected_buildings"),
    [
        (None, ["小吃部", "水木生活中心", "水木餐廳"]),
        ("", ["小吃部", "水木生活中心", "水木餐廳"]),
        ("小吃部", ["小吃部"]),
        ("水木", ["水木生活中心", "水木餐廳"]),
        ("水木生活中心", ["水木生活中心", "水木餐廳"]),
    ],
)
async def test_dining_grouped_limits_over_protocol(
    monkeypatch, dining_candidates, check_open, building, expected_buildings
):
    data = [
        {
            "building": name,
            "restaurants": (
                [{"name": "Pizza", "note": ""} for _ in range(12)]
                + [
                    {"name": "Sushi closed", "note": "平日休息、週六休息、週日休息"}
                    for _ in range(12)
                ]
                + [
                    {
                        "name": f"Sushi-{index}",
                        "phone": None,
                        "schedule": {"weekday": "09:00-17:00"},
                        "note": "",
                    }
                    for index in range(count)
                ]
            ),
        }
        for name, count in [("小吃部", 11), ("水木生活中心", 23), ("水木餐廳", 35)]
    ]
    data.append({"building": "Empty", "restaurants": []})
    original = deepcopy(data)
    calls = []

    async def fake_get(endpoint):
        assert endpoint == "dining.json"
        calls.append(endpoint)
        return "testhash", data

    monkeypatch.setattr(nthudata, "get", fake_get)
    async with Client(mcp) as client:
        response = await client.call_tool(
            "find_dining",
            {"building": building, "restaurant_name": "Sushi", "check_open": check_open},
        )
    assert not response.is_error
    assert set(response.data) == {"buildings"}
    expected = []
    for b in data:
        if b["building"] not in expected_buildings:
            continue
        restaurants = [
            r
            for r in b["restaurants"]
            if r["name"].startswith("Sushi") and (not check_open or not r["note"])
        ]
        if not building:
            restaurants = restaurants[:10]
        expected.append(
            {
                "building": b["building"],
                "restaurants": [
                    {
                        "name": r["name"],
                        "phone": r.get("phone"),
                        "schedule": r.get("schedule"),
                        "note": r["note"] or None,
                    }
                    for r in restaurants
                ],
            }
        )
    assert response.data == {"buildings": expected}
    assert data == original
    assert calls == ["dining.json"]


@pytest.mark.parametrize("check_open", [None, "today", "weekday", "saturday", "sunday"])
async def test_dining_omits_empty_buildings(monkeypatch, dining_candidates, check_open):
    async def fake_get(endpoint):
        assert endpoint == "dining.json"
        return "testhash", [
            {"building": "Empty", "restaurants": []},
            {
                "building": "Closed",
                "restaurants": [{"name": "Cafe", "note": "平日休息、週六休息、週日休息"}],
            },
        ]

    monkeypatch.setattr(nthudata, "get", fake_get)
    async with Client(mcp) as client:
        response = await client.call_tool("find_dining", {"check_open": check_open})
    assert not response.is_error
    if check_open:
        assert response.data == {"buildings": []}
    else:
        assert [b["building"] for b in response.data["buildings"]] == ["Closed"]


@pytest.fixture
def directory_and_locations(monkeypatch):
    datasets = {
        "directory.json": [
            {
                "index": str(index),
                "name": "Office",
                "details": {
                    "people": [
                        {"name": "Alice", "title": "Director"},
                        {"name": "Alice Smith", "title": None},
                        {"name": "Bob", "title": "Director"},
                        {"name": "Carol"},
                        {"name": "Dave", "title": ""},
                    ]
                },
            }
            for index in range(8)
        ],
        "maps.json": {
            "main": {
                "Main gate": {"latitude": "24.79", "longitude": "120.99"},
                **{
                    f"Main hall {index}": {"latitude": "24.79", "longitude": "120.99"}
                    for index in range(7)
                },
            },
        },
    }
    original = deepcopy(datasets)
    calls = []

    async def get_dataset(path):
        calls.append(path)
        return "test-version", datasets[path]

    monkeypatch.setattr(nthudata, "get", get_dataset)
    yield datasets, calls
    assert datasets == original


@pytest.mark.parametrize("fuzzy", [None, True, False])
@pytest.mark.parametrize(
    "query,department_count,person_names",
    [
        ("Office", 5, []),
        ("Alice", 0, ["Alice"] * 8),
        ("Director", 0, ["Alice", "Bob"] * 5),
        ("Off", 0, []),
        ("Ali", 0, []),
        ("Dir", 0, []),
        ("office", 0, []),
        ("alice", 0, []),
        ("director", 0, []),
        ("ZZZZZZ", 0, []),
        ("", 0, []),
    ],
)
async def test_registered_directory_search_modes(
    directory_and_locations, query, department_count, person_names, fuzzy
):
    arguments = {"query": query}
    if fuzzy is not None:
        arguments["fuzzy"] = fuzzy
    async with Client(mcp) as client:
        response = await client.call_tool("search_directory", arguments)
    assert not response.is_error
    assert set(response.data) == {"departments", "people"}
    assert directory_and_locations[1] == ["directory.json"]
    if fuzzy is False or query in ("ZZZZZZ", ""):
        assert len(response.data["departments"]) == department_count
        assert [person["name"] for person in response.data["people"]] == person_names
    else:
        expected_departments = 5 if query.lower() in ("office", "off") else 0
        assert len(response.data["departments"]) == expected_departments
        if expected_departments:
            assert response.data["departments"] == directory_and_locations[0]["directory.json"][:5]
        elif query == "alice":
            assert [person["name"] for person in response.data["people"]] == (
                ["Alice"] * 8 + ["Alice Smith"] * 2
            )
        elif query.lower() in ("alice", "ali"):
            assert [person["name"] for person in response.data["people"]] == [
                "Alice",
                "Alice Smith",
            ] * 5
        else:
            assert [person["name"] for person in response.data["people"]] == ["Alice", "Bob"] * 5


@pytest.mark.parametrize("fuzzy", [None, True, False])
@pytest.mark.parametrize("query", ["Main gate", "Main", "main gate", "ZZZZZZ", ""])
async def test_registered_locations_search_modes(directory_and_locations, query, fuzzy):
    arguments = {"query": query}
    if fuzzy is not None:
        arguments["fuzzy"] = fuzzy
    async with Client(mcp) as client:
        response = await client.call_tool("search_locations", arguments)
    assert not response.is_error
    assert set(response.data) == {"locations"}
    assert directory_and_locations[1] == ["maps.json"]
    locations = response.data["locations"]
    if fuzzy is False:
        assert [location["name"] for location in locations] == (
            ["Main gate"] if query == "Main gate" else []
        )
    elif query in ("ZZZZZZ", ""):
        assert locations == []
    else:
        assert len(locations) == 5
        assert locations[0]["name"] == "Main gate"


@pytest.mark.parametrize("fuzzy", [True, False])
@pytest.mark.parametrize(
    "tool,path", [("search_directory", "directory.json"), ("search_locations", "maps.json")]
)
async def test_search_tools_unavailable_dataset(monkeypatch, tool, path, fuzzy):
    async def unavailable(endpoint):
        assert endpoint == path
        raise DataNotAvailableException("private upstream")

    monkeypatch.setattr(nthudata, "get", unavailable)
    async with Client(mcp) as client:
        response = await client.call_tool(
            tool, {"query": "query", "fuzzy": fuzzy}, raise_on_error=False
        )
    assert response.is_error
    assert "private upstream" not in str(response.content)


@pytest.mark.parametrize("fuzzy", [True, False])
async def test_empty_directory_search_unavailable_dataset(monkeypatch, fuzzy):
    async def unavailable(endpoint):
        assert endpoint == "directory.json"
        raise DataNotAvailableException("private upstream")

    monkeypatch.setattr(nthudata, "get", unavailable)
    async with Client(mcp) as client:
        response = await client.call_tool(
            "search_directory", {"query": "", "fuzzy": fuzzy}, raise_on_error=False
        )
    assert response.is_error
    assert "private upstream" not in str(response.content)


@pytest.mark.parametrize("tool", ["search_directory", "search_locations"])
async def test_search_tools_protocol_validation(tool):
    async with Client(mcp) as client:
        for arguments in ({}, {"query": "query", "fuzzy": "invalid"}):
            response = await client.call_tool(tool, arguments, raise_on_error=False)
            assert response.is_error
        removed = await client.call_tool("search_campus", {"query": "query"}, raise_on_error=False)
        assert removed.is_error


@pytest.mark.parametrize("query", ["Office", "Alice", "Director", "Ali", "alice", "director"])
async def test_directory_exact_rest_shape_and_case(directory_and_locations, query):
    _, departments = await get_runtime().departments.get_directory(query, fuzzy=False)
    if query == "Office":
        assert departments == directory_and_locations[0]["directory.json"]
    elif query in ("Alice", "Director"):
        assert len(departments) == 8
        for department in departments:
            expected = ["Alice"] if query == "Alice" else ["Alice", "Bob"]
            assert [person["name"] for person in department["details"]["people"]] == expected
    else:
        assert departments == []


@pytest.mark.parametrize("fuzzy", [True, False])
async def test_directory_filters_before_caps_and_preserves_exact_order(monkeypatch, fuzzy):
    data = [
        {"index": str(index), "name": "ZZZZZZ", "details": {"people": [{"name": "ZZZZZZ"}]}}
        for index in range(20)
    ] + [
        {
            "index": str(index),
            "name": "Office",
            "details": {"people": [{"name": "Alice"}]},
        }
        for index in range(20, 28)
    ]

    async def get_dataset(path):
        assert path == "directory.json"
        return "test-version", data

    monkeypatch.setattr(nthudata, "get", get_dataset)
    async with Client(mcp) as client:
        departments = await client.call_tool(
            "search_directory", {"query": "Office", "fuzzy": fuzzy}
        )
        people = await client.call_tool("search_directory", {"query": "Alice", "fuzzy": fuzzy})
    assert [department["index"] for department in departments.data["departments"]] == [
        str(index) for index in range(20, 25)
    ]
    assert people.data == {"departments": [], "people": [{"name": "Alice"}] * 8}
