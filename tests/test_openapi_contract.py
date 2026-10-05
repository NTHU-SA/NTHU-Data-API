"""Pin the public structure and match representative real responses to declarations."""

import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from data_api.api.api import app
from data_api.api.schemas.calendars import CalendarEvent
from data_api.api.schemas.errors import ErrorResponse, ValidationErrorResponse
from data_api.api.schemas.responses import COUNT_HEADERS, DATA_VERSION_HEADERS
from data_api.checks.openapi import contract_differences, contract_projection
from data_api.domain.calendars.services import calendars_service

BASELINE = Path(__file__).parent / "fixtures" / "openapi_contract.json"


def test_structured_openapi_baseline():
    expected = json.loads(BASELINE.read_text(encoding="utf-8"))
    changes = contract_differences(expected, contract_projection(app.openapi()))
    assert not changes, "\n".join(changes)


@pytest.mark.parametrize("change", ["route", "parameter", "operationId", "default", "response"])
def test_compatibility_check_identifies_structural_changes(change):
    expected = contract_projection(app.openapi())
    actual = deepcopy(expected)
    operation = actual["operations"]["GET /courses"]
    match change:
        case "route":
            del actual["operations"]["GET /courses"]
            location = "GET /courses"
        case "parameter":
            del operation["parameters"]["query:teacher"]
            location = "query:teacher"
        case "operationId":
            operation["operationId"] = "unexpectedRename"
            location = "operationId"
        case "default":
            operation["parameters"]["query:type"]["schema"]["default"] = "xclass"
            location = "query:type.schema.default"
        case "response":
            del operation["responses"]["503"]
            location = "responses.503"
    assert any(location in difference for difference in contract_differences(expected, actual))


def test_documentation_changes_are_ignored_but_title_fields_are_not():
    schema = deepcopy(app.openapi())
    expected = contract_projection(schema)
    schema["paths"]["/courses"]["get"]["description"] = "New documentation"
    schema["components"]["schemas"]["CourseData"]["properties"]["id"]["description"] = "New label"
    assert contract_projection(schema) == expected
    assert "title" in expected["schemas"]["LibraryRssItem"]["properties"]
    del schema["components"]["schemas"]["LibraryRssItem"]["properties"]["title"]
    assert contract_differences(expected, contract_projection(schema))


def test_every_snapshot_operation_documents_availability_and_headers():
    schema = app.openapi()
    live_prefixes = ("/energy/", "/libraries/space", "/libraries/lost")
    for path, methods in schema["paths"].items():
        for operation in methods.values():
            responses = operation["responses"]
            if path.startswith(live_prefixes):
                assert "503" not in responses
                assert "X-Data-Commit-Hash" not in responses["200"].get("headers", {})
                continue
            assert responses["503"]["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/ErrorResponse"
            }, path
            headers = responses["200"]["headers"]
            counted = path.startswith("/courses") or path == "/calendars/{calendar_id}/events"
            assert headers == (COUNT_HEADERS if counted else DATA_VERSION_HEADERS), path


def test_manual_errors_and_course_validation_have_body_schemas():
    schema = app.openapi()
    for path, methods in schema["paths"].items():
        for operation in methods.values():
            for status in ["400", "404", "500", "502", "503", "504"]:
                if status in operation["responses"]:
                    assert operation["responses"][status]["content"]["application/json"][
                        "schema"
                    ] == {"$ref": "#/components/schemas/ErrorResponse"}, (path, status)
    detail = schema["components"]["schemas"]["ValidationErrorResponse"]["properties"]["detail"]
    assert {choice["type"] for choice in detail["anyOf"]} == {"string", "array"}
    assert schema["components"]["schemas"]["LibraryRssItem"]["properties"]["link"]["anyOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]


def assert_error_matches_schema(response, schema_path, status, method="get"):
    assert response.status_code == status
    declared = app.openapi()["paths"][schema_path][method]["responses"][str(status)]
    ref = declared["content"]["application/json"]["schema"]["$ref"]
    model = ValidationErrorResponse if ref.endswith("ValidationErrorResponse") else ErrorResponse
    model.model_validate(response.json())
    assert float(response.headers["X-Process-Time"]) >= 0


@pytest.mark.parametrize(
    "url,schema_path,status,detail_type",
    [
        ("/calendars/missing", "/calendars/{calendar_id}", 404, str),
        (
            "/calendars/missing/events?start=2026-10-02&end=2026-10-01",
            "/calendars/{calendar_id}/events",
            400,
            str,
        ),
        ("/courses?type=invalid", "/courses", 422, list),
        ("/courses?teacher=%5B", "/courses", 422, str),
    ],
)
async def test_actual_manual_and_validation_errors(
    dataset_runtime, url, schema_path, status, detail_type
):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(url)
    assert_error_matches_schema(response, schema_path, status)
    assert isinstance(response.json()["detail"], detail_type)


async def test_snapshot_unavailable_matches_openapi():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/libraries/rss/news")
    assert_error_matches_schema(response, "/libraries/rss/{rss_type}", 503)
    assert "X-Data-Commit-Hash" not in response.headers


@pytest.mark.parametrize("timeout,status", [(False, 502), (True, 504)])
async def test_live_upstream_error_matches_openapi(mock_upstream, timeout, status):
    def upstream(request):
        if timeout:
            raise httpx.ReadTimeout("private upstream timeout")
        return httpx.Response(503)

    mock_upstream(upstream)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/libraries/spaces")
    assert_error_matches_schema(response, "/libraries/spaces", status)


async def test_calendar_pagination_body_and_headers_match_openapi(monkeypatch):
    events = [
        {
            "id": f"event-{index}",
            "title": "Event",
            "start": "2026-10-01",
            "end": "2026-10-02",
            "all_day": True,
        }
        for index in range(3)
    ]

    async def search(*args, **kwargs):
        return "calendar-version", events

    monkeypatch.setattr(calendars_service, "search_calendar_events", search)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/calendars/academic/events?limit=1&offset=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    CalendarEvent.model_validate(response.json()[0])
    assert response.headers["X-Total-Count"] == "3"
    assert response.headers["X-Data-Commit-Hash"] == "calendar-version"
    declared = app.openapi()["paths"]["/calendars/{calendar_id}/events"]["get"]["responses"]["200"]
    assert declared["headers"] == COUNT_HEADERS
