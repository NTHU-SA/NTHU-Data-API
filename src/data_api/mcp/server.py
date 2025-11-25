"""
NTHU Data API MCP Server.

Curated MCP tools designed for LLM agents, following agent-first design principles:
1. Minimal tool count - combine related functionality
2. LLM-friendly names and descriptions in natural language
3. Reasonable defaults to hide complexity
4. Focus on agent stories rather than API structure

These tools are designed to answer common questions about NTHU campus life.
"""

from datetime import datetime
from typing import Literal, Optional

from fastmcp import FastMCP

from data_api.domain.announcements import services as announcements_services
from data_api.domain.buses import services as buses_services
from data_api.domain.courses import models as courses_models
from data_api.domain.courses import services as courses_services
from data_api.domain.departments import services as departments_services
from data_api.domain.dining import services as dining_services
from data_api.domain.energy import services as energy_services
from data_api.domain.locations import services as locations_services
from data_api.domain.newsletters import services as newsletters_services

# Create curated MCP server
mcp = FastMCP(
    name="NTHU Campus Assistant",
    instructions="""You are an assistant for National Tsing Hua University (NTHU) in Taiwan.
You can help with:
- Finding campus locations and directions
- Checking bus schedules and next arrivals
- Searching for courses
- Getting campus announcements
- Finding restaurants and dining options
- Checking library information
- Getting newsletter updates
- Checking real-time electricity usage

Always respond in the user's language (Traditional Chinese or English).
""",
)


# Tool implementation functions (can be tested directly)


async def _search_campus(query: str) -> dict:
    """
    Search for campus locations, departments, or people.

    Args:
        query: Search term - can be a location name, department name, or person's name.

    Returns:
        Dictionary with locations, departments, and people matching the query.
    """
    # Search locations
    _, locations = await locations_services.locations_service.fuzzy_search_locations(query=query)

    # Search departments and people
    _, dept_results = await departments_services.departments_service.fuzzy_search_departments_and_people(
        query=query
    )

    return {
        "locations": locations[:5] if locations else [],
        "departments": dept_results.get("departments", [])[:5],
        "people": dept_results.get("people", [])[:10],
    }


async def _get_next_buses(
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
) -> dict:
    """
    Get upcoming bus departures for campus routes.

    Args:
        route: Bus route type - 'main' for main campus loop, 'nanda' for Nanda shuttle, 'all' for both.
        direction: Direction - 'up' (toward TSMC Building/Nanda), 'down' (toward Main Gate/Main Campus), 'all' for both.
        limit: Maximum number of buses to return (default 5).

    Returns:
        Dictionary with upcoming bus schedules and route information.
    """
    await buses_services.buses_service.update_data()

    current = datetime.now()
    current_time = current.time().strftime("%H:%M")
    current_day = "weekday" if current.weekday() < 5 else "weekend"

    # Get detailed schedules
    raw_data = buses_services.buses_service.get_schedule(
        route_type=route,
        day=current_day,
        direction=direction,
        detailed=True,
    )

    # Filter to buses after current time
    filtered = buses_services.after_specific_time(
        raw_data,
        current_time,
        ["dep_info", "time"],
    )

    # Format response
    buses = []
    for bus in filtered[:limit]:
        dep_info = bus.get("dep_info", {})
        buses.append({
            "departure_time": dep_info.get("time"),
            "departure_stop": dep_info.get("dep_stop"),
            "description": dep_info.get("description"),
            "bus_type": bus.get("bus_type"),
            "stops": bus.get("stops_time", []),
        })

    return {
        "current_time": current_time,
        "day_type": current_day,
        "buses": buses,
        "route_info": buses_services.buses_service.get_route_info(
            route if route != "all" else None,
            direction if direction != "all" else None,
        ),
    }


async def _search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Search for courses at NTHU.

    Args:
        keyword: Search in course titles (Chinese or English).
        teacher: Teacher name to search for.
        course_id: Specific course ID to look up.
        limit: Maximum number of results to return (default 20).

    Returns:
        Dictionary with matching courses.
    """
    # Build search conditions
    conditions_list = []

    if keyword:
        # Search both Chinese and English titles
        conditions_list.append(
            [
                {"row_field": "chinese_title", "matcher": keyword, "regex_match": True},
                "or",
                {"row_field": "english_title", "matcher": keyword, "regex_match": True},
            ]
        )

    if teacher:
        teacher_cond = {"row_field": "teacher", "matcher": teacher, "regex_match": True}
        if conditions_list:
            conditions_list = [conditions_list[0], "and", teacher_cond]
        else:
            conditions_list.append(teacher_cond)

    if course_id:
        id_cond = {"row_field": "id", "matcher": course_id, "regex_match": True}
        if conditions_list:
            if isinstance(conditions_list[0], list):
                conditions_list = [conditions_list[0], "and", id_cond]
            else:
                conditions_list = [conditions_list[0], "and", id_cond]
        else:
            conditions_list.append(id_cond)

    if not conditions_list:
        # Return all courses if no filter specified
        courses = courses_services.courses_service.course_data[:limit]
    else:
        # Build and execute query
        if len(conditions_list) == 1:
            query_target = conditions_list[0]
        else:
            query_target = conditions_list

        condition = courses_models.Conditions(list_build_target=query_target)
        courses = courses_services.courses_service.query(condition)[:limit]

    # Format response
    return {
        "count": len(courses),
        "courses": [
            {
                "id": c.id,
                "chinese_title": c.chinese_title,
                "english_title": c.english_title,
                "teacher": c.teacher,
                "credit": c.credit,
                "time_and_room": c.class_room_and_time,
                "language": c.language.value if hasattr(c.language, "value") else str(c.language),
                "note": c.note if c.note else None,
            }
            for c in courses
        ],
    }


async def _get_announcements(
    department: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    Get campus announcements.

    Args:
        department: Filter by department name (fuzzy match).
        keyword: Search in announcement titles.
        limit: Maximum number of announcements per department (default 10).

    Returns:
        Dictionary with announcements grouped by department.
    """
    _, data = await announcements_services.announcements_service.fuzzy_search_announcements(
        department=department,
        title=keyword,
    )

    # Format response - limit articles per department
    result = []
    for source in data[:10]:  # Limit departments
        articles = source.get("articles", [])[:limit]
        if articles:
            result.append({
                "department": source.get("department"),
                "language": source.get("language"),
                "articles": [
                    {
                        "title": a.get("title"),
                        "link": a.get("link"),
                        "date": a.get("date"),
                    }
                    for a in articles
                ],
            })

    return {
        "count": sum(len(d["articles"]) for d in result),
        "sources": result,
    }


async def _find_dining(
    restaurant_name: Optional[str] = None,
    building: Optional[str] = None,
    check_open: Literal["today", "weekday", "saturday", "sunday"] = None,
) -> dict:
    """
    Find dining options on campus.

    Args:
        restaurant_name: Search for restaurant by name.
        building: Filter by building name (e.g., '小吃部', '水木').
        check_open: Check which restaurants are open - 'today', 'weekday', 'saturday', or 'sunday'.

    Returns:
        Dictionary with restaurant information.
    """
    if check_open:
        _, restaurants = await dining_services.dining_service.get_open_restaurants(
            schedule=check_open
        )
        return {
            "schedule": check_open,
            "open_restaurants": [
                {
                    "name": r.get("name"),
                    "area": r.get("area"),
                    "phone": r.get("phone"),
                    "schedule": r.get("schedule"),
                }
                for r in restaurants[:20]
            ],
        }
    else:
        _, data = await dining_services.dining_service.fuzzy_search_dining_data(
            building_name=building,
            restaurant_name=restaurant_name,
        )

        # Format response
        buildings = []
        for b in data:
            restaurants = b.get("restaurants", [])
            if restaurants:
                buildings.append({
                    "building": b.get("building"),
                    "restaurants": [
                        {
                            "name": r.get("name"),
                            "phone": r.get("phone"),
                            "schedule": r.get("schedule"),
                            "note": r.get("note") if r.get("note") else None,
                        }
                        for r in restaurants[:10]
                    ],
                })

        return {
            "buildings": buildings,
        }


async def _get_library_info(
    info_type: Literal["space", "lost_and_found"] = "space",
) -> dict:
    """
    Get library information.

    Args:
        info_type: Type of information - 'space' for study space availability, 'lost_and_found' for lost items.

    Returns:
        Dictionary with library information.
    """
    import ssl

    import httpx
    import truststore

    ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    if info_type == "space":
        url = "https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx"
        try:
            async with httpx.AsyncClient(verify=ctx) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if data.get("resmsg") != "成功":
                    return {"error": "Unable to fetch space data"}

                spaces = data.get("rows", [])
                return {
                    "spaces": [
                        {
                            "zone": s.get("zonename"),
                            "type": s.get("spacetypename"),
                            "available": s.get("count"),
                        }
                        for s in spaces
                    ]
                }
        except Exception as e:
            return {"error": f"Failed to fetch library space: {str(e)}"}

    elif info_type == "lost_and_found":
        import re
        from datetime import timedelta

        from bs4 import BeautifulSoup

        date_end = datetime.now()
        date_start = date_end - timedelta(days=6 * 30)

        post_data = {
            "place": "0",
            "date_start": date_start.strftime("%Y-%m-%d"),
            "date_end": date_end.strftime("%Y-%m-%d"),
            "catalog": "ALL",
            "keyword": "",
            "SUMIT": "送出",
        }
        url = "https://adage.lib.nthu.edu.tw/find/search_it.php"

        try:
            async with httpx.AsyncClient(verify=ctx) as client:
                response = await client.post(url, data=post_data, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.find("table")
                if not table:
                    return {"items": []}

                table_rows = table.find_all("tr")
                if not table_rows:
                    return {"items": []}

                table_title = [td.text.strip() for td in table_rows[0].find_all("td")]
                items = []
                for row in table_rows[1:11]:  # Limit to 10 items
                    cells = [re.sub(r"\s+", " ", td.text.strip()) for td in row.find_all("td")]
                    if len(cells) == len(table_title):
                        items.append(dict(zip(table_title, cells)))

                return {"items": items}
        except Exception as e:
            return {"error": f"Failed to fetch lost and found: {str(e)}"}

    return {"error": "Invalid info_type"}


async def _get_newsletters(
    search: Optional[str] = None,
) -> dict:
    """
    Get campus newsletter information.

    Args:
        search: Optional search term to filter newsletter names.

    Returns:
        Dictionary with newsletter information.
    """
    _, newsletters = await newsletters_services.newsletters_service.get_all_newsletters()

    if search:
        from thefuzz import fuzz

        newsletters = [
            n for n in newsletters
            if fuzz.partial_ratio(search, n.get("name", "")) >= 60
        ]

    return {
        "count": len(newsletters),
        "newsletters": [
            {
                "name": n.get("name"),
                "link": n.get("link"),
                "latest_articles": [
                    {"title": a.get("title"), "date": a.get("date")}
                    for a in n.get("articles", [])[:3]
                ],
            }
            for n in newsletters[:15]
        ],
    }


async def _get_energy_usage() -> dict:
    """
    Get real-time electricity usage for campus.

    Returns:
        Dictionary with current electricity usage by zone.
    """
    try:
        data = await energy_services.energy_service.get_realtime_electricity_usage()
        return {
            "zones": [
                {
                    "name": item.get("name"),
                    "usage_kw": item.get("data"),
                    "capacity_kw": item.get("capacity"),
                    "usage_percent": round(item.get("data", 0) / item.get("capacity", 1) * 100, 1),
                    "last_updated": item.get("last_updated"),
                }
                for item in data
            ]
        }
    except Exception as e:
        return {"error": f"Failed to fetch energy data: {str(e)}"}


async def _get_bus_stops() -> dict:
    """
    Get all bus stop locations on campus.

    Returns:
        Dictionary with bus stop names and coordinates.
    """
    await buses_services.buses_service.update_data()
    stops = buses_services.buses_service.gen_bus_stops_info()

    return {
        "stops": [
            {
                "name": s.get("name"),
                "name_en": s.get("name_en"),
                "latitude": s.get("latitude"),
                "longitude": s.get("longitude"),
            }
            for s in stops
        ]
    }


# Register MCP tools (wrapping the implementation functions)


@mcp.tool(
    description="Search for campus locations, departments, or people at NTHU. "
    "Use this to find where buildings are, contact info for departments, or look up staff members."
)
async def search_campus(query: str) -> dict:
    """Search for campus locations, departments, or people."""
    return await _search_campus(query)


@mcp.tool(
    description="Get the next available campus buses. "
    "Use this when someone asks about bus schedules, when the next bus is, or how to get around campus."
)
async def get_next_buses(
    route: Literal["main", "nanda", "all"] = "all",
    direction: Literal["up", "down", "all"] = "all",
    limit: int = 5,
) -> dict:
    """Get upcoming bus departures for campus routes."""
    return await _get_next_buses(route, direction, limit)


@mcp.tool(
    description="Search for courses at NTHU. "
    "Use this to find courses by name, teacher, time, or other criteria."
)
async def search_courses(
    keyword: Optional[str] = None,
    teacher: Optional[str] = None,
    course_id: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Search for courses at NTHU."""
    return await _search_courses(keyword, teacher, course_id, limit)


@mcp.tool(
    description="Get campus announcements from NTHU departments. "
    "Use this to find news, notices, or updates from campus offices."
)
async def get_announcements(
    department: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Get campus announcements."""
    return await _get_announcements(department, keyword, limit)


@mcp.tool(
    description="Find restaurants and dining options on campus. "
    "Use this to find where to eat, check which restaurants are open, or search for specific food."
)
async def find_dining(
    restaurant_name: Optional[str] = None,
    building: Optional[str] = None,
    check_open: Literal["today", "weekday", "saturday", "sunday"] = None,
) -> dict:
    """Find dining options on campus."""
    return await _find_dining(restaurant_name, building, check_open)


@mcp.tool(
    description="Get library information including space availability and lost items. "
    "Use this to check if study spaces are available or to find lost items."
)
async def get_library_info(
    info_type: Literal["space", "lost_and_found"] = "space",
) -> dict:
    """Get library information."""
    return await _get_library_info(info_type)


@mcp.tool(
    description="Get campus newsletter information. "
    "Use this to find electronic newsletters from various NTHU departments."
)
async def get_newsletters(
    search: Optional[str] = None,
) -> dict:
    """Get campus newsletter information."""
    return await _get_newsletters(search)


@mcp.tool(
    description="Get real-time campus electricity usage. "
    "Use this to check current power consumption on campus."
)
async def get_energy_usage() -> dict:
    """Get real-time electricity usage for campus."""
    return await _get_energy_usage()


@mcp.tool(
    description="Get information about bus stops on campus. "
    "Use this to find bus stop locations and which buses stop there."
)
async def get_bus_stops() -> dict:
    """Get all bus stop locations on campus."""
    return await _get_bus_stops()

