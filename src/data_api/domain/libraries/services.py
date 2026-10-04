"""
Libraries domain service.

Handles library data fetching and search, plus the library RSS feeds
crawled by NTHU-Data-Scraper.
"""

import re
import ssl
from datetime import datetime, timedelta
from typing import Optional

import httpx
import truststore
from bs4 import BeautifulSoup
from pydantic import TypeAdapter
from thefuzz import fuzz

from data_api.api.schemas.libraries import LibraryLostAndFound, LibrarySpace
from data_api.core.exceptions import (
    DataNotAvailableException,
    UpstreamException,
    UpstreamResponseException,
)
from data_api.core.upstream import upstream_errors
from data_api.data.manager import nthudata

JSON_PATH = "libraries.json"
RSS_JSON_PATH = "libraries/rss.json"
FUZZY_SEARCH_THRESHOLD = 70
DATASET_UNAVAILABLE = "Dataset temporarily unavailable"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}
SPACE_ADAPTER = TypeAdapter(list[LibrarySpace])
ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def parse_lost_items(html: str) -> list[dict[str, str]]:
    """Parse complete results, distinguishing an empty page from a broken one."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        content = soup.find(id="content")
        if content is None:
            raise UpstreamResponseException("Lost-and-found results table is missing")
        heading = content.find("h1")
        if heading is None:
            raise UpstreamResponseException("Lost-and-found results table is missing")
        if "Lost and Found System" in heading.get_text() and re.search(
            r"\u76ee\u524d\u7121\u8cc7\u6599\s*!!", content.get_text()
        ):
            return []
        raise UpstreamResponseException("Lost-and-found results table is missing")

    rows = table.find_all("tr")
    if not rows:
        raise UpstreamResponseException("Lost-and-found table has no header")
    titles = [cell.get_text(strip=True) for cell in rows[0].find_all(["td", "th"])]
    column_names = set(titles)
    if column_names != set(LibraryLostAndFound.model_fields) or len(titles) != len(column_names):
        raise UpstreamResponseException("Lost-and-found table has invalid columns")

    items = []
    for row in rows[1:]:
        cells = [
            re.sub(r"\s+", " ", cell.get_text().strip()) for cell in row.find_all(["td", "th"])
        ]
        if len(cells) != len(titles):
            raise UpstreamResponseException("Lost-and-found row has invalid cells")
        items.append(dict(zip(titles, cells)))
    return items


class LibrariesService:
    """Service for library data operations."""

    async def get_space_availability(self) -> list[dict]:
        """Get validated live library space data."""
        with upstream_errors():
            async with httpx.AsyncClient(verify=ctx) as client:
                response = await client.get(
                    "https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx",
                    headers=DEFAULT_HEADERS,
                )
                response.raise_for_status()
                data = response.json()

            if not isinstance(data, dict) or not isinstance(data.get("resmsg"), str):
                raise UpstreamResponseException("Library space response has no result message")
            if data["resmsg"] != "\u6210\u529f":
                raise UpstreamException("Library space service reported a failure")
            rows = data.get("rows")
            if not isinstance(rows, list):
                raise UpstreamResponseException("Library space response has no rows list")
            SPACE_ADAPTER.validate_python(rows)
            return rows

    async def get_lost_and_found_items(self) -> list[dict[str, str]]:
        """Get all live lost items from the last six months."""
        date_end = datetime.now()
        date_start = date_end - timedelta(days=6 * 30)
        post_data = {
            "place": "0",
            "date_start": date_start.strftime("%Y-%m-%d"),
            "date_end": date_end.strftime("%Y-%m-%d"),
            "catalog": "ALL",
            "keyword": "",
            "SUMIT": "\u9001\u51fa",
        }
        with upstream_errors():
            async with httpx.AsyncClient(verify=ctx) as client:
                response = await client.post(
                    "https://adage.lib.nthu.edu.tw/find/search_it.php",
                    data=post_data,
                    headers=DEFAULT_HEADERS,
                )
                response.raise_for_status()
            return parse_lost_items(response.text)

    async def get_all_libraries(self) -> tuple[Optional[str], list[dict]]:
        """Get all libraries."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException(DATASET_UNAVAILABLE)
        return result

    async def get_library_by_name(self, name: str) -> tuple[Optional[str], Optional[dict]]:
        """Get library by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException(DATASET_UNAVAILABLE)

        commit_hash, libraries_data = result
        for library in libraries_data:
            if library["name"] == name:
                return commit_hash, library
        return commit_hash, None

    async def fuzzy_search_libraries(self, query: str) -> tuple[Optional[str], list[dict]]:
        """Fuzzy search libraries by name."""
        result = await nthudata.get(JSON_PATH)
        if result is None:
            raise DataNotAvailableException(DATASET_UNAVAILABLE)

        commit_hash, libraries_data = result
        results_with_score = []
        for library in libraries_data:
            similarity = fuzz.partial_ratio(query, library["name"])
            if similarity >= FUZZY_SEARCH_THRESHOLD:
                results_with_score.append((similarity, library))

        results_with_score.sort(key=lambda x: x[0], reverse=True)
        return commit_hash, [lib for _, lib in results_with_score]

    async def get_rss_items(self, rss_type: str) -> tuple[Optional[str], Optional[list[dict]]]:
        """Get the items of one library RSS feed."""
        result = await nthudata.get(RSS_JSON_PATH)
        if result is None:
            raise DataNotAvailableException(DATASET_UNAVAILABLE)

        commit_hash, rss_data = result
        return commit_hash, rss_data.get(rss_type)


# Global service instance
libraries_service = LibrariesService()
