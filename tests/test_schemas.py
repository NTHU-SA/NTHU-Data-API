"""Response fields distinguish optional metadata from required dataset structure."""

import pytest
from pydantic import ValidationError

from data_api.api.schemas.announcements import AnnouncementArticle
from data_api.api.schemas.departments import DepartmentPerson
from data_api.api.schemas.dining import DiningRestaurant
from data_api.api.schemas.libraries import (
    LibraryCalendar,
    LibraryCalendarEvent,
    LibraryRssData,
    LibraryRssImage,
    LibraryRssItem,
)
from data_api.api.schemas.newsletters import NewsletterArticle


@pytest.mark.parametrize(
    "model,payload,optional_fields",
    [
        (AnnouncementArticle, {}, {"title", "link", "date"}),
        (NewsletterArticle, {}, {"title", "link", "date"}),
        (DepartmentPerson, {"name": "Test"}, {"title", "extension", "email", "note"}),
        (
            DiningRestaurant,
            {"area": "Test", "name": "Test", "note": "", "phone": "", "schedule": {}},
            {"image"},
        ),
        (LibraryRssImage, {}, {"url", "title", "link"}),
        (
            LibraryRssItem,
            {"title": "Test", "description": ""},
            {"guid", "category", "link", "pubDate", "author", "image"},
        ),
        (LibraryRssData, {"link": "https://example.com"}, {"title", "date"}),
        (
            LibraryCalendar,
            {"id": "main", "url": "https://example.com"},
            {"name", "description", "timezone"},
        ),
        (
            LibraryCalendarEvent,
            {
                "id": "event",
                "title": "Test",
                "start": "2026-09-28",
                "end": "2026-09-29",
                "all_day": True,
            },
            {"description"},
        ),
    ],
)
def test_optional_metadata_can_be_omitted_or_null(model, payload, optional_fields):
    omitted = model.model_validate(payload)
    explicit_null = model.model_validate({**payload, **{name: None for name in optional_fields}})
    assert omitted.model_dump() == explicit_null.model_dump()
    for name in optional_fields:
        assert getattr(omitted, name) is None
        assert not model.model_fields[name].is_required()
    for name in payload:
        assert model.model_fields[name].is_required()
        missing_required = {key: value for key, value in payload.items() if key != name}
        with pytest.raises(ValidationError):
            model.model_validate(missing_required)


@pytest.mark.parametrize("invalid_link", ["https://", "not a url"])
def test_optional_urls_still_validate_supplied_values(invalid_link):
    with pytest.raises(ValidationError):
        AnnouncementArticle(link=invalid_link)
