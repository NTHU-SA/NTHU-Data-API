"""Offline upstream fixtures for API smoke tests."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from data_api.data.manager import nthudata
from data_api.data.nthudata import Snapshot
from data_api.models.courses import CourseData


def course_payload(**overrides):
    data = {
        "id": "11510TEST100000",
        "chinese_title": "Test course",
        "english_title": "Test Course",
        "note": "",
        "limit_note": "",
        "object": "",
        "ge_type": "",
        "ge_category": "",
        "no_extra_selection": "",
        "semester_code": "11510",
        "department_code": "TEST",
        "course_number": "100000",
        "department_name": None,
        "college_name": None,
        "course_level_code": None,
        "course_level": None,
        "remote_teaching": None,
        "credits": 3,
        "capacity": None,
        "capacity_unlimited": True,
        "enrolled_count": None,
        "enrollment_after_selection": None,
        "enrollment_after_withdrawal": None,
        "reserved_for_freshmen": 0,
        "is_cancelled": False,
        "language_code": "zh",
        "lecturers": [],
        "meetings": [],
        "expertises": [],
        "programs": [],
        "curriculum_requirements": [],
        "prerequisite_text": "",
        "parsing_issues": [],
    }
    return data | overrides


def make_course(data=None, **overrides):
    return CourseData.model_validate(course_payload(**((data or {}) | overrides)))


def set_courses(monkeypatch, courses, version="course-test-version"):
    from data_api.domain.courses.services import courses_service

    snapshot = Snapshot([], courses, version, datetime.now(timezone.utc))
    monkeypatch.setattr(courses_service, "get_snapshot", AsyncMock(return_value=snapshot))
    return snapshot


NEWSLETTER_NAMES = ["NTHU-Newsletter", "教務處綜合教務組電子報"]


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    async def unavailable(self, request):
        return httpx.Response(503, request=request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", unavailable)


@pytest.fixture
def mock_upstream(monkeypatch, no_external_network):
    def install(handler):
        transport = httpx.MockTransport(handler)

        async def handle_request(self, request):
            return await transport.handle_async_request(request)

        monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", handle_request)

    return install


@pytest.fixture
def library_space_payload():
    return {
        "resmsg": "成功",
        "rows": [
            {
                "spacetype": "1",
                "spacetypename": "Study room",
                "zoneid": "main",
                "zonename": "Main library",
                "count": "12",
            }
        ],
    }


@pytest.fixture
def lost_items_html():
    def make(count=12):
        header = "<tr><td>序號</td><td>拾獲時間</td><td>拾獲地點</td><td>描述</td></tr>"
        rows = "".join(
            f"<tr><td>{index}</td><td>2026-09-30</td><td>Main library</td>"
            "<td> Book\n  title </td></tr>"
            for index in range(count)
        )
        return f"<table>{header}{rows}</table>"

    return make


@pytest.fixture
def lost_items_empty_page():
    return '<div id="content"><h1>失物招領系統 Lost and Found System</h1>' "<br>目前無資料 !!</div>"


@pytest.fixture
async def dataset_runtime():
    data = {
        "/courses/latest.json": [course_payload()],
        "/courses/sources.json": {"semesters": ["11510"]},
        "/buses.json": {},
        "/calendars.json": [],
        "/libraries/calendars.json": [],
        "/announcements.json": [],
        "/announcements_list.json": [],
        "/dining.json": [],
        "/directory.json": [],
        "/newsletters.json": [
            {"name": name, "link": "https://example.com", "details": {}, "articles": []}
            for name in NEWSLETTER_NAMES
        ],
        "/maps.json": {
            "main": {
                name: {"latitude": "24.79", "longitude": "120.99"}
                for name in ["校門", "綜合", "台積", "台達"]
            }
        },
    }

    def handler(request):
        if request.url.path == "/file_details.json":
            return httpx.Response(
                200,
                json={
                    "file_details": {
                        "/": [{"name": path.lstrip("/"), "version": "fixture"} for path in data]
                    }
                },
            )
        if request.url.path in data:
            return httpx.Response(200, json=data[request.url.path])
        return httpx.Response(404)

    async with nthudata.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        yield nthudata
