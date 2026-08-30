"""Tests for the combined application lifespan.

``app`` is a ``combined_app`` that merges the MCP routes with the FastAPI routes.
Because it only copies the *routes* of ``fast_api_app``, the lifespan declared on
that app is not carried over and has to be chained explicitly. These tests guard
against that wiring regressing again, which would silently leave every
startup-loaded service empty.

Note: the MCP session manager may only be started once per process, so the real
lifespan is entered exactly once here, by ``TestCoursesAfterStartup``.
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


class TestCoursesAfterStartup:
    """Tests that the real lifespan is attached to the app that gets served."""

    async def test_courses_endpoint_returns_data_after_startup(self):
        """Test /courses/ is populated once the app's own lifespan has run.

        ``courses_service`` is only filled during startup and no route refreshes
        it, so a lifespan that is not wired up makes this endpoint return an
        empty list with a 200 status code.
        """
        async with app.router.lifespan_context(app):
            assert courses_services.courses_service.course_data, "courses data was not loaded"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
            ) as client:
                response = await client.get("/courses/")

        assert response.status_code == 200
        assert len(response.json()) > 0
