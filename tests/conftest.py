"""Offline upstream fixtures for API smoke tests."""

from copy import deepcopy

import httpx
import pytest

from data_api.api.schemas.newsletters import NewsletterName
from data_api.data.manager import nthudata


@pytest.fixture
def published_library_rss():
    """URL cases from the 2026-09-30 publication, with abbreviated articles."""
    items = [
        {
            "title": "ProQuest trial",
            "description": "<p>Trial details</p>",
            "link": (
                "https://www.proquest.com/centralpremium/index, "
                "https://ebookcentral.proquest.com/lib/nthutw/home.action, "
                "https://www.proquest.com/pq1entertainmentpopularculture, "
                "https://www.proquest.com/pq1history, https://forms.gle/65YaF7R1z52VU9S19"
            ),
            "publisher_metadata": {"retain": True},
        },
        {
            "title": "HyRead trial",
            "description": "Trial details",
            "link": (
                "https://hyread.cc/2026Ericdata, "
                "https://nthu.primo.exlibrisgroup.com/permalink/"
                "886UST_NTHU/1ij8ggp/alma990057064270206774"
            ),
        },
        {
            "title": "Database form",
            "description": "Trial details",
            "link": (
                "https://docs.google.com/forms/d/e/"
                "1FAIpQLSem85ICMXMGn0mQczfz6dHd6v6b0BK5JnN8A03-uNk4Xz_Hjg/viewform?usp=header, "
                "https://nthu.primo.exlibrisgroup.com/permalink/"
                "886UST_NTHU/1ij8ggp/alma9957360263506774"
            ),
        },
        {
            "title": "CNKI trial",
            "description": "Trial details",
            "link": (
                "https://oversea.cnki.net/tra,https://book.oversea.cnki.net/tra,"
                "https://thinker.oversea.cnki.net/tra"
            ),
            "image": {
                "url": "https://www.lib.nthu.edu.tw/image/news/19/20260921_LRS_CNKI Trial.jpg",
                "publisher_metadata": {"retain": True},
            },
        },
        {
            "title": "Wiley trial",
            "description": "Trial details",
            "link": (
                "https://nthu.primo.exlibrisgroup.com/permalink/"
                "886UST_NTHU/1ij8ggp/alma990057112140206774"
            ),
            "image": {
                "url": "https://www.lib.nthu.edu.tw/image/news/19/20260717_LRS_Wiley UBCM.jpg"
            },
        },
    ]
    return {
        "news": deepcopy(items),
        "eresources": deepcopy(items),
        "exhibit": [{"title": "Exhibit", "description": "", "link": "https://example.com/"}],
        "branches": [{"title": "Branch news", "description": "", "link": None, "image": None}],
    }


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    async def unavailable(self, request):
        return httpx.Response(503, request=request)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", unavailable)


@pytest.fixture
async def dataset_runtime():
    data = {
        "/courses.json": [
            {"id": "11410TEST100000", "chinese_title": "Test course", "language": "中"}
        ],
        "/buses.json": {},
        "/calendars.json": [],
        "/announcements.json": [],
        "/announcements_list.json": [],
        "/dining.json": [],
        "/directory.json": [],
        "/newsletters.json": [
            {"name": name.value, "link": "https://example.com", "details": {}, "articles": []}
            for name in NewsletterName
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
                        "/": [{"name": path.lstrip("/"), "last_commit": "fixture"} for path in data]
                    }
                },
            )
        if request.url.path in data:
            return httpx.Response(200, json=data[request.url.path])
        return httpx.Response(404)

    async with nthudata.lifespan(httpx.AsyncClient(transport=httpx.MockTransport(handler))):
        yield nthudata
