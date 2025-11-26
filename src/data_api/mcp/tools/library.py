"""Library information MCP tool."""

from datetime import datetime
from typing import Literal

from data_api.mcp.server import mcp


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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

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


@mcp.tool(
    description="Get library information including space availability and lost items. "
    "Use this to check if study spaces are available or to find lost items."
)
async def get_library_info(
    info_type: Literal["space", "lost_and_found"] = "space",
) -> dict:
    """Get library information."""
    return await _get_library_info(info_type)
