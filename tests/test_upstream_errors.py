"""REST and MCP contracts for live upstream failures."""

import json

import httpx
import pytest
from fastmcp import Client

from data_api.api.api import app, mcp_app
from data_api.domain.energy.services import energy_service
from data_api.domain.libraries.services import libraries_service
from data_api.mcp.server import mcp

LIVE_CALLS = [
    pytest.param(
        "/energy/electricity",
        "get_energy_usage",
        {},
        energy_service,
        "get_realtime_electricity_usage",
        id="energy-current",
    ),
    pytest.param(
        "/energy/electricity_usage",
        "get_energy_usage",
        {},
        energy_service,
        "get_realtime_electricity_usage",
        id="energy",
    ),
    pytest.param(
        "/libraries/spaces",
        "get_library_info",
        {"info_type": "space"},
        libraries_service,
        "get_space_availability",
        id="spaces-current",
    ),
    pytest.param(
        "/libraries/space",
        "get_library_info",
        {"info_type": "space"},
        libraries_service,
        "get_space_availability",
        id="space",
    ),
    pytest.param(
        "/libraries/lost-and-found",
        "get_library_info",
        {"info_type": "lost_and_found"},
        libraries_service,
        "get_lost_and_found_items",
        id="lost-items-current",
    ),
    pytest.param(
        "/libraries/lost_and_found",
        "get_library_info",
        {"info_type": "lost_and_found"},
        libraries_service,
        "get_lost_and_found_items",
        id="lost-items",
    ),
]
CALL_PARAMETERS = "path,tool,arguments,service,method"
LOST_ITEM_HEADERS = (
    "\u5e8f\u865f",
    "\u62fe\u7372\u6642\u9593",
    "\u62fe\u7372\u5730\u9ede",
    "\u63cf\u8ff0",
)


@pytest.fixture
async def rest():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.parametrize(CALL_PARAMETERS, LIVE_CALLS)
@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.WriteTimeout,
        httpx.PoolTimeout,
        httpx.ConnectError,
        httpx.ReadError,
        httpx.RequestError,
        403,
        404,
        500,
        503,
    ],
)
async def test_live_http_failures(
    rest, mock_upstream, caplog, path, tool, arguments, service, method, failure
):
    def handler(request):
        if isinstance(failure, int):
            return httpx.Response(failure, text="Private upstream response")
        raise failure("Private upstream exception", request=request)

    mock_upstream(handler)
    timed_out = not isinstance(failure, int) and issubclass(failure, httpx.TimeoutException)
    status = 504 if timed_out else 502
    detail = "Upstream request timed out" if timed_out else "Upstream service unavailable"

    response = await rest.get(path, headers={"Origin": "https://example.com"})
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert float(response.headers["X-Process-Time"]) >= 0
    async with Client(mcp) as client:
        result = await client.call_tool(tool, arguments, raise_on_error=False)
    assert result.is_error
    assert result.content[0].text == detail
    assert result.data is None
    assert any(record.exc_info for record in caplog.records)
    assert "Traceback" in caplog.text
    assert "http" in caplog.text if isinstance(failure, int) else "Private upstream" in caplog.text


@pytest.mark.parametrize(CALL_PARAMETERS, LIVE_CALLS)
async def test_unexpected_live_failures_are_safe(
    rest, monkeypatch, caplog, path, tool, arguments, service, method
):
    async def fail():
        raise RuntimeError("Private internal failure at https://upstream.example")

    monkeypatch.setattr(service, method, fail)
    response = await rest.get(path, headers={"Origin": "https://example.com"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert float(response.headers["X-Process-Time"]) >= 0
    async with Client(mcp) as client:
        result = await client.call_tool(tool, arguments, raise_on_error=False)
    assert result.is_error
    assert result.content[0].text == "Internal server error"
    assert "Private internal failure" in caplog.text


@pytest.mark.parametrize(
    "path,tool,arguments,body",
    [
        ("/energy/electricity_usage", "get_energy_usage", {}, ""),
        ("/energy/electricity_usage", "get_energy_usage", {}, '<img alt="kW: --">'),
        ("/libraries/space", "get_library_info", {"info_type": "space"}, "Private invalid JSON"),
        ("/libraries/space", "get_library_info", {"info_type": "space"}, b'"\xff"'),
        ("/libraries/space", "get_library_info", {"info_type": "space"}, "[]"),
        ("/libraries/space", "get_library_info", {"info_type": "space"}, "null"),
        ("/libraries/space", "get_library_info", {"info_type": "space"}, "{}"),
        (
            "/libraries/space",
            "get_library_info",
            {"info_type": "space"},
            json.dumps({"resmsg": "\u6210\u529f"}),
        ),
        (
            "/libraries/space",
            "get_library_info",
            {"info_type": "space"},
            json.dumps({"resmsg": "\u6210\u529f", "rows": None}),
        ),
        (
            "/libraries/space",
            "get_library_info",
            {"info_type": "space"},
            json.dumps({"resmsg": "\u6210\u529f", "rows": [{}]}),
        ),
        (
            "/libraries/lost_and_found",
            "get_library_info",
            {"info_type": "lost_and_found"},
            "<html>Private upstream login page</html>",
        ),
        (
            "/libraries/lost_and_found",
            "get_library_info",
            {"info_type": "lost_and_found"},
            "<table></table>",
        ),
        (
            "/libraries/lost_and_found",
            "get_library_info",
            {"info_type": "lost_and_found"},
            "<table><tr><td>Unexpected column</td></tr></table>",
        ),
        (
            "/libraries/lost_and_found",
            "get_library_info",
            {"info_type": "lost_and_found"},
            "<p>\u76ee\u524d\u7121\u8cc7\u6599 !!</p>",
        ),
    ],
)
async def test_invalid_live_responses(rest, mock_upstream, path, tool, arguments, body):
    mock_upstream(lambda request: httpx.Response(200, content=body))
    response = await rest.get(path)
    assert response.status_code == 502
    assert response.json() == {"detail": "Invalid response from upstream service"}
    async with Client(mcp) as client:
        result = await client.call_tool(tool, arguments, raise_on_error=False)
    assert result.is_error
    assert result.content[0].text == "Invalid response from upstream service"


@pytest.mark.parametrize("invalid_row_position", [0, 11])
async def test_malformed_lost_rows_are_not_skipped(
    rest, mock_upstream, lost_items_html, invalid_row_position
):
    html = lost_items_html().replace(
        f"<td>{invalid_row_position}</td>", "<td>incomplete</td><td>extra cell</td>"
    )
    mock_upstream(lambda request: httpx.Response(200, text=html))
    response = await rest.get("/libraries/lost_and_found")
    assert response.status_code == 502
    assert response.json() == {"detail": "Invalid response from upstream service"}
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_library_info", {"info_type": "lost_and_found"}, raise_on_error=False
        )
    assert result.is_error
    assert result.content[0].text == "Invalid response from upstream service"


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param((*LOST_ITEM_HEADERS, "Internal note"), id="extra"),
        pytest.param((*LOST_ITEM_HEADERS, LOST_ITEM_HEADERS[-1]), id="duplicate"),
        pytest.param(LOST_ITEM_HEADERS[:-1], id="missing"),
    ],
)
async def test_lost_items_reject_invalid_headers(rest, mock_upstream, headers):
    header = "".join(f"<th>{title}</th>" for title in headers)
    cells = "".join(f"<td>{index}</td>" for index in range(len(headers)))
    html = f"<table><tr>{header}</tr><tr>{cells}</tr></table>"
    mock_upstream(lambda request: httpx.Response(200, text=html))

    response = await rest.get("/libraries/lost_and_found")
    assert response.status_code == 502
    assert response.json() == {"detail": "Invalid response from upstream service"}
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_library_info", {"info_type": "lost_and_found"}, raise_on_error=False
        )
    assert result.is_error
    assert result.content[0].text == "Invalid response from upstream service"


@pytest.mark.parametrize("count", [0, 12])
async def test_lost_items_accept_reordered_headers(rest, mock_upstream, count):
    serial, found_at, location, description = LOST_ITEM_HEADERS
    headers = (description, location, serial, found_at)
    html = "<table><tr>" + "".join(f"<th> {title} </th>" for title in headers) + "</tr>"
    items = []
    for index in range(count):
        values = {
            serial: str(index),
            found_at: "2026-09-30",
            location: "Main library",
            description: " Book\n  title ",
        }
        items.append({**values, description: "Book title"})
        html += "<tr>" + "".join(f"<td>{values[title]}</td>" for title in headers) + "</tr>"
    html += "</table>"
    mock_upstream(lambda request: httpx.Response(200, text=html))

    response = await rest.get("/libraries/lost_and_found")
    assert response.status_code == 200
    assert response.json() == items
    async with Client(mcp) as client:
        result = await client.call_tool("get_library_info", {"info_type": "lost_and_found"})
    assert not result.is_error
    assert result.data == {"items": items[:10]}


@pytest.mark.parametrize(
    "html",
    [
        pytest.param(
            "<h1>Lost and Found System</h1>\u76ee\u524d\u7121\u8cc7\u6599 !!",
            id="missing-content",
        ),
        pytest.param(
            '<div id="content">\u76ee\u524d\u7121\u8cc7\u6599 !!</div>', id="missing-heading"
        ),
        pytest.param(
            '<div id="content"><h1>Library News</h1>\u76ee\u524d\u7121\u8cc7\u6599 !!</div>',
            id="wrong-heading",
        ),
        pytest.param(
            '<div id="content"><h1>Lost and Found System</h1>Results pending</div>',
            id="missing-empty-marker",
        ),
    ],
)
async def test_lost_items_reject_invalid_empty_pages(rest, mock_upstream, html):
    mock_upstream(lambda request: httpx.Response(200, text=html))

    response = await rest.get("/libraries/lost_and_found")
    assert response.status_code == 502
    assert response.json() == {"detail": "Invalid response from upstream service"}
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_library_info", {"info_type": "lost_and_found"}, raise_on_error=False
        )
    assert result.is_error
    assert result.content[0].text == "Invalid response from upstream service"


async def test_library_space_application_failure(rest, mock_upstream):
    mock_upstream(
        lambda request: httpx.Response(
            200, json={"resmsg": "Private upstream rejection", "rows": []}
        )
    )
    response = await rest.get("/libraries/space")
    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream service unavailable"}
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_library_info", {"info_type": "space"}, raise_on_error=False
        )
    assert result.is_error
    assert result.content[0].text == "Upstream service unavailable"


@pytest.mark.parametrize(CALL_PARAMETERS, LIVE_CALLS)
@pytest.mark.parametrize("empty_page", ["table", "message"])
async def test_live_protocol_success(
    rest,
    mock_upstream,
    library_space_payload,
    lost_items_html,
    lost_items_empty_page,
    path,
    tool,
    arguments,
    service,
    method,
    empty_page,
):
    def handler(request):
        if request.url.host == "140.114.188.86":
            return httpx.Response(200, text='<img alt="kW: 0">')
        if request.url.host == "libsms.lib.nthu.edu.tw":
            return httpx.Response(200, json={**library_space_payload, "rows": []})
        html = lost_items_html(0) if empty_page == "table" else lost_items_empty_page
        return httpx.Response(200, text=html)

    mock_upstream(handler)
    response = await rest.get(path)
    assert response.status_code == 200
    async with Client(mcp) as client:
        result = await client.call_tool(tool, arguments)
    assert not result.is_error
    if tool == "get_energy_usage":
        assert len(result.data["zones"]) == len(response.json()) == 3
        assert all(zone["usage_kw"] == 0 for zone in result.data["zones"])
    else:
        assert response.json() == []
        assert result.data == {"spaces" if arguments["info_type"] == "space" else "items": []}


@pytest.mark.parametrize(CALL_PARAMETERS, LIVE_CALLS)
async def test_mcp_http_failure_is_tool_error(
    rest, mock_upstream, path, tool, arguments, service, method
):
    def handler(request):
        raise httpx.ReadTimeout("Private upstream exception", request=request)

    mock_upstream(handler)
    async with mcp_app.lifespan(app):
        response = await rest.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            },
        )
    assert response.status_code == 200
    messages = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert len(messages) == 1
    assert "error" not in messages[0]
    result = messages[0]["result"]
    assert result["isError"] is True
    assert result["content"][0]["text"] == "Upstream request timed out"
