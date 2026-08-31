"""Tests for the combined application lifespan.

``app`` is a ``combined_app`` that merges the MCP routes with the FastAPI routes.
Because it only copies the *routes* of ``fast_api_app``, the lifespan declared on
that app is not carried over and has to be chained explicitly. These tests guard
against that wiring regressing again, which would silently leave every
startup-loaded service empty.

Note: the MCP session manager may only be started once per process, so its
lifespan is stubbed out here. The data layer is stubbed as well, which keeps
these tests off the network and makes them fail for one reason only: the
lifespan wiring being broken.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from data_api.api import api as api_module
from data_api.api.api import app
from data_api.core import config
from data_api.data.manager import nthudata
from data_api.domain.buses import services as buses_services
from data_api.domain.courses import services as courses_services


@asynccontextmanager
async def _noop_lifespan(app):
    """Stand in for the MCP lifespan, which cannot be started twice."""
    yield


class TestCombinedLifespan:
    """Tests for the startup tasks chained into the combined lifespan."""

    async def test_runs_startup_tasks_in_order(self, monkeypatch):
        """Test the combined lifespan pre-fetches data and updates both services."""
        calls = []

        async def fake_prefetch(endpoints):
            calls.append(("prefetch", list(endpoints)))
            return {endpoint: True for endpoint in endpoints}

        async def fake_buses_update():
            calls.append(("buses", None))

        async def fake_courses_update():
            calls.append(("courses", None))

        monkeypatch.setattr(api_module, "mcp_app", SimpleNamespace(lifespan=_noop_lifespan))
        monkeypatch.setattr(nthudata, "prefetch", fake_prefetch)
        monkeypatch.setattr(buses_services.buses_service, "update_data", fake_buses_update)
        monkeypatch.setattr(courses_services.courses_service, "update_data", fake_courses_update)

        async with api_module.combined_lifespan(app):
            pass

        assert [name for name, _ in calls] == ["prefetch", "buses", "courses"]
        assert calls[0][1] == config.PREFETCH_ENDPOINTS

    async def test_reports_failed_endpoints_as_ascii(self, monkeypatch, capsys):
        """Test the startup report stays ASCII so non-UTF-8 consoles do not fail."""

        async def fake_prefetch(endpoints):
            return {endpoint: index == 0 for index, endpoint in enumerate(endpoints)}

        async def noop():
            return None

        monkeypatch.setattr(api_module, "mcp_app", SimpleNamespace(lifespan=_noop_lifespan))
        monkeypatch.setattr(nthudata, "prefetch", fake_prefetch)
        monkeypatch.setattr(buses_services.buses_service, "update_data", noop)
        monkeypatch.setattr(courses_services.courses_service, "update_data", noop)

        async with api_module.combined_lifespan(app):
            pass

        output = capsys.readouterr().out
        assert "[OK]" in output
        assert "[FAIL]" in output
        output.encode("ascii")


FAKE_COURSE = {
    "id": "11410TEST100000",
    "chinese_title": "測試課程",
    "english_title": "Test Course",
    "credit": "3",
    "size_limit": "50",
    "freshman_reservation": "0",
    "object": "",
    "ge_type": "",
    "language": "中",
    "note": "",
    "suspend": "",
    "class_room_and_time": "T3T4",
    "teacher": "測試教師",
    "prerequisite": "",
    "limit_note": "",
    "expertise": "",
    "program": "",
    "no_extra_selection": "",
    "required_optional_note": "",
}


async def _fake_get(endpoint_name: str):
    """Serve in-memory data in place of a request to data.nthusa.tw."""
    if endpoint_name.endswith("courses.json"):
        return ("testcommithash", [FAKE_COURSE])
    return ("testcommithash", {})


class TestCoursesAfterStartup:
    """Tests that the app's own lifespan is attached to the app that gets served."""

    async def test_courses_endpoint_returns_data_after_startup(self, monkeypatch):
        """Test /courses/ is populated once the app's own lifespan has run.

        ``courses_service`` is only filled during startup and no route refreshes
        it, so a lifespan that is not wired up makes this endpoint return an
        empty list with a 200 status code. The data layer is stubbed so that the
        real ``update_data`` runs against fixed data: this test then fails only
        when the lifespan wiring itself is broken.
        """
        monkeypatch.setattr(api_module, "mcp_app", SimpleNamespace(lifespan=_noop_lifespan))
        monkeypatch.setattr(nthudata, "get", _fake_get)
        monkeypatch.setattr(courses_services.courses_service, "course_data", [])

        async with app.router.lifespan_context(app):
            assert courses_services.courses_service.course_data, "courses data was not loaded"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
            ) as client:
                response = await client.get("/courses/")

        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["chinese_title"] == "測試課程"
