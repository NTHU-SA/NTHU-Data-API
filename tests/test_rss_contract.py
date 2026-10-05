"""Publisher URL regressions must survive candidate installation and REST serialization."""

import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from pydantic import HttpUrl, TypeAdapter, ValidationError
from test_data_manager import Clock, Publisher

from data_api.api.api import app
from data_api.api.schemas.libraries import LibraryRssImage, LibraryRssItem
from data_api.data.manager import nthudata
from data_api.data.nthudata import Freshness
from data_api.data.validation import validate_dataset

FIXTURE = Path(__file__).parent / "fixtures" / "library_rss_published_urls.json"


@pytest.fixture
def published_rss():
    # URL values from the 2026-09-30 publication; article text is abbreviated.
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixed_cases_reproduce_original_single_uri_failures(published_rss):
    adapter = TypeAdapter(HttpUrl)
    for item in published_rss["news"][1:]:
        with pytest.raises(ValidationError):
            adapter.validate_json(json.dumps(item["link"]), strict=True)
    with pytest.raises(ValidationError):
        adapter.validate_json(json.dumps(published_rss["news"][0]["image"]["url"]), strict=True)


def test_full_rss_candidate_preserves_text_and_unknown_fields(published_rss):
    original = deepcopy(published_rss)
    normalized = validate_dataset("/libraries/rss.json", published_rss)
    assert published_rss == original
    assert normalized["news"][0]["link"] == original["news"][0]["link"]
    assert normalized["news"][0]["publisher_item_field"] == "retained"
    assert normalized["news"][0]["image"]["publisher_image_field"] == "retained"
    for feed in ["news", "eresources"]:
        assert normalized[feed][0]["image"]["url"].endswith("CNKI%20Trial.jpg")
    assert validate_dataset("/libraries/rss.json", normalized) == normalized
    for items in normalized.values():
        for item in items:
            LibraryRssItem.model_validate(item).model_dump_json()


@pytest.mark.parametrize("value", ["https://", "not a url", 42])
def test_invalid_images_still_fail(value):
    with pytest.raises(ValidationError):
        LibraryRssImage(url=value)


@pytest.mark.parametrize("value", [42, True, [], {}])
def test_rss_link_remains_nullable_text(value):
    with pytest.raises(ValidationError):
        LibraryRssItem(title="News", description="", link=value)


async def test_rss_cold_start_refresh_and_last_known_good(monkeypatch, published_rss):
    clock = Clock()
    publisher = Publisher(published_rss, "libraries/rss.json")
    monkeypatch.setattr(nthudata, "clock", clock)
    async with nthudata.lifespan(publisher.client()):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for version in ["a", "b"]:
                publisher.version = version
                for feed, expected in published_rss.items():
                    response = await client.get(f"/libraries/rss/{feed}")
                    assert response.status_code == 200
                    assert response.headers["X-Data-Commit-Hash"] == version
                    assert len(response.json()) == len(expected)
                    for actual, original in zip(response.json(), expected, strict=True):
                        assert actual["link"] == original["link"]
                    if expected:
                        assert response.json()[0]["link"] == expected[0]["link"]
                        assert response.json()[0]["image"]["url"].endswith("CNKI%20Trial.jpg")
                state = nthudata.state_for("libraries/rss.json")
                assert state.snapshot.raw["news"][0]["image"]["url"].endswith("CNKI%20Trial.jpg")
                assert state.snapshot.raw is state.snapshot.data
                clock.advance()
            snapshot = state.snapshot
            publisher.version = "invalid"
            publisher.payload = deepcopy(published_rss)
            publisher.payload["news"][0]["image"]["url"] = "https://"
            response = await client.get("/libraries/rss/news")
            assert response.status_code == 200
            assert response.headers["X-Data-Commit-Hash"] == "b"
            assert state.snapshot is snapshot
            assert state.freshness == Freshness.STALE
            assert state.last_error.category == "validation"


async def test_invalid_rss_without_snapshot_returns_503(published_rss):
    published_rss["news"][0]["image"]["url"] = "https://"
    publisher = Publisher(published_rss, "libraries/rss.json")
    async with nthudata.lifespan(publisher.client()):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/libraries/rss/news")
    assert response.status_code == 503
    assert response.json() == {"detail": "Service temporarily unavailable"}
