"""Tests for dining endpoints."""

from copy import deepcopy
from datetime import datetime, timezone
from itertools import product

import pytest
from httpx import ASGITransport, AsyncClient

from data_api.api import schemas
from data_api.api.api import app
from data_api.data.manager import nthudata
from data_api.domain.dining import services

pytestmark = pytest.mark.usefixtures("dataset_runtime")


@pytest.fixture
def dining_candidates(monkeypatch):
    data = [
        {
            "building": building,
            "restaurants": [
                {
                    "area": building,
                    "name": f"{name}-{day}",
                    "note": note,
                    "phone": "",
                    "image": None,
                    "schedule": {},
                }
                for name in ["Pizza", "Sushi"]
                for day, note in [
                    ("always", ""),
                    ("weekday", "平日休息"),
                    ("saturday", "週六休息"),
                    ("sunday", "週日休息"),
                ]
            ],
        }
        for building in ["小吃部", "水木生活中心"]
    ] + [{"building": "其他餐廳", "restaurants": []}]
    original = deepcopy(data)
    calls = []

    async def fake_get(endpoint):
        calls.append(endpoint)
        return "testhash", data

    class Saturday(datetime):
        @classmethod
        def now(cls, tz=None):
            assert str(tz) == "Asia/Taipei"
            return cls(2026, 9, 25, 16, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(nthudata, "get", fake_get)
    monkeypatch.setattr(services, "datetime", Saturday)
    yield data, calls
    assert data == original


class TestDiningEndpoints:
    """Tests for dining endpoints."""

    @pytest.fixture
    async def client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
        ) as client:
            yield client

    async def test_get_all_dining(self, client: AsyncClient):
        """Test getting all dining information."""
        response = await client.get("/dining")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "building_name",
        [_.value for _ in schemas.dining.DiningBuildingName],
    )
    async def test_get_dining_by_building(self, client: AsyncClient, building_name: str):
        """Test getting dining information filtered by building."""
        params = {"building_name": building_name}
        response = await client.get("/dining", params=params)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "schedule",
        [_.value for _ in schemas.dining.DiningScheduleName],
    )
    async def test_get_open_restaurants(self, client: AsyncClient, schedule: str):
        """Test getting open restaurants by schedule."""
        params = {"schedule": schedule}
        response = await client.get("/dining/", params=params)
        assert response.status_code == 200

    @pytest.mark.parametrize("schedule", [None, "today", "weekday", "saturday", "sunday"])
    @pytest.mark.parametrize("fuzzy", [True, False])
    @pytest.mark.parametrize("building_filter,name_filter", list(product([False, True], repeat=2)))
    async def test_combined_filters(
        self, client, dining_candidates, schedule, fuzzy, building_filter, name_filter
    ):
        data, calls = dining_candidates
        params = {"fuzzy": fuzzy}
        if schedule is not None:
            params["schedule"] = schedule
        if building_filter:
            params["building_name"] = "水木生活中心"
        if name_filter:
            params["restaurant_name"] = "Sushi"
        response = await client.get("/dining/", params=params)
        assert response.status_code == 200
        day = "saturday" if schedule == "today" else schedule
        # Preserve the existing heuristic: Sunday's single-character "日" also matches "平日".
        excluded = {
            None: (),
            "weekday": ("weekday",),
            "saturday": ("saturday",),
            "sunday": ("weekday", "sunday"),
        }[day]
        expected = []
        for building in data:
            if building_filter and building["building"] != "水木生活中心":
                continue
            restaurants = [
                restaurant
                for restaurant in building["restaurants"]
                if (not name_filter or restaurant["name"].startswith("Sushi"))
                and not restaurant["name"].endswith(excluded)
            ]
            if restaurants or (schedule is None and fuzzy and not name_filter):
                expected.append({**building, "restaurants": restaurants})
        assert response.json() == expected
        assert response.headers["X-Data-Commit-Hash"] == "testhash"
        assert calls == ["dining.json"]

    @pytest.mark.parametrize("fuzzy", [True, False])
    @pytest.mark.parametrize(
        "filters",
        [
            {"restaurant_name": "ZZZZZZ"},
            {"building_name": "其他餐廳"},
        ],
    )
    async def test_no_schedule_matches(self, client, dining_candidates, fuzzy, filters):
        response = await client.get(
            "/dining/", params={**filters, "schedule": "saturday", "fuzzy": fuzzy}
        )
        assert response.status_code == 200
        assert response.json() == []
        assert dining_candidates[1] == ["dining.json"]

    @pytest.mark.parametrize("fuzzy", [True, False])
    async def test_all_restaurants_closed(self, client, dining_candidates, monkeypatch, fuzzy):
        data = deepcopy(dining_candidates[0])
        for building in data:
            for restaurant in building["restaurants"]:
                restaurant["note"] = "週六休息"
        original = deepcopy(data)

        async def fake_get(endpoint):
            return "testhash", data

        monkeypatch.setattr(nthudata, "get", fake_get)
        response = await client.get("/dining/", params={"schedule": "saturday", "fuzzy": fuzzy})
        assert response.status_code == 200
        assert response.json() == []
        assert data == original

    @pytest.mark.parametrize("fuzzy", [True, False])
    async def test_schedule_respects_search_mode(self, client, dining_candidates, fuzzy):
        response = await client.get(
            "/dining/",
            params={"schedule": "saturday", "restaurant_name": "Susi", "fuzzy": fuzzy},
        )
        assert response.status_code == 200
        names = [r["name"] for b in response.json() for r in b["restaurants"]]
        assert names == (["Sushi-always", "Sushi-weekday", "Sushi-sunday"] * 2 if fuzzy else [])

    @pytest.mark.parametrize("schedule", ["", "monday", "now"])
    async def test_invalid_schedule(self, client, dining_candidates, schedule):
        response = await client.get("/dining/", params={"schedule": schedule})
        assert response.status_code == 422
        assert dining_candidates[1] == []

    @pytest.mark.parametrize("fuzzy", [True, False])
    async def test_unversioned_data(self, client, dining_candidates, monkeypatch, fuzzy):
        data, calls = dining_candidates

        async def fake_get(endpoint):
            calls.append(endpoint)
            return None, data

        monkeypatch.setattr(nthudata, "get", fake_get)
        response = await client.get("/dining/", params={"schedule": "saturday", "fuzzy": fuzzy})
        assert response.status_code == 200
        assert response.json()
        assert "X-Data-Commit-Hash" not in response.headers
        assert calls == ["dining.json"]

    async def test_open_route_removed(self, client):
        response = await client.get("/dining/open", params={"schedule": "today"})
        assert response.status_code == 404


def test_dining_openapi_contract():
    schema = app.openapi()
    assert "/dining/open" not in schema["paths"]
    operation = schema["paths"]["/dining"]["get"]
    assert operation["operationId"] == "getDiningData"
    parameter = next(p for p in operation["parameters"] if p["name"] == "schedule")
    assert parameter["required"] is False
    assert parameter["in"] == "query"
    assert {"$ref": "#/components/schemas/DiningScheduleName"} in parameter["schema"]["anyOf"]
    assert schema["components"]["schemas"]["DiningScheduleName"]["enum"] == [
        "today",
        "weekday",
        "saturday",
        "sunday",
    ]
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["type"] == "array"
    assert response["items"] == {"$ref": "#/components/schemas/DiningBuilding"}
