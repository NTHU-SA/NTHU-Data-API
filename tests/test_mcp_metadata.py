"""Regression tests for public MCP tool names and display titles."""

from fastmcp import Client

from data_api.mcp.server import mcp


async def test_tool_names_and_titles_exposed_to_clients():
    expected = {
        "search_campus": "搜尋校園資訊",
        "get_next_buses": "查詢接下來的公車班次",
        "get_bus_stops": "查詢公車站點資訊",
        "search_courses": "搜尋課程列表",
        "get_announcements": "搜尋校園公告",
        "find_dining": "搜尋餐廳列表",
        "get_library_info": "查詢圖書館資訊",
        "get_newsletters": "搜尋電子報列表",
        "get_energy_usage": "查詢校園即時用電",
    }

    async with Client(mcp) as client:
        tools = await client.list_tools()

    assert len(tools) == len(expected)
    assert {tool.name: tool.title for tool in tools} == expected
    assert all(tool.description for tool in tools)
