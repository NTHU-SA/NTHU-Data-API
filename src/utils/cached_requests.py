from urllib.parse import urlparse, urlunparse

import requests
from cachetools import Cache
from fastapi import HTTPException

cache = Cache(maxsize=1024)


def generate_headers(referer: str) -> dict:
    return {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-CN;q=0.5",
        "dnt": "1",
        "referer": referer,
        "sec-ch-ua": "'Chromium';v='119', 'Microsoft Edge';v='119', 'Not:A-Brand';v='24'",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "Android",
        "sec-fetch-dest": "script",
        "sec-fetch-mode": "no-cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36 Edg/112.0.1722.48",
    }


def validate_url(url: str) -> str:
    """
    驗證網址是否使用 http 和 https 協議，且僅為 nthu.edu.tw 網域。

    Args:
        url (str): 網址。
    Returns:
        str: 經過驗證的網址。
    Raises:
        ValueError: 當網址不合法時。
    """

    parsed_url = urlparse(url)

    # 確認 URL 是否包含 scheme 和 netloc
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Invalid URL")

    # 只允許 http 或 https 協議
    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError("Invalid URL scheme")

    # 只允許 nthu.edu.tw 結尾 或 清華JOB讚 的網域
    if not (
        parsed_url.netloc.endswith("nthu.edu.tw")
        or parsed_url.netloc.endswith("goodjob-nthu.conf.asia")
    ):
        raise ValueError("Invalid URL domain")

    # 重新組合 URL，排除可能的用戶名和密碼
    safe_url = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )

    return safe_url


def delete(url: str) -> None:
    """
    刪除快取中的網址（若有）。

    Args:
        url (str): 網址。
    """

    if url in cache:
        del cache[url]


def get(
    url: str,
    update: bool = False,
    auto_headers: bool = True,
    **kwargs,
) -> tuple[str, bool]:
    """
    從網址取得回應內容。

    Args:
        url (str): 網址。
        update (bool): 是否更新快取。
        auto_headers (bool): 是否自動生成 headers。
        **kwargs: 額外傳遞給的參數，會傳遞給 requests.get。

    Returns:
        tuple[str, bool]: 回應內容和是否使用快取。
    """

    # 驗證網址
    try:
        url = validate_url(url)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # 如果不更新快取且有先前快取，則直接回傳快取內容
    if not update and url in cache:
        return cache[url], True

    # 若無快取或需更新快取，則重新發送請求
    try:
        headers = generate_headers(url) if auto_headers else None

        response = requests.get(url, headers, timeout=10, **kwargs)

        status_code = response.status_code
        # 如果回應狀態碼不是 200，則拋出例外；但有可能是 2xx 範圍的狀態碼
        if status_code != 200:
            raise HTTPException(status_code, f"Request error: {status_code}")

        response_text = response.text
        cache[url] = response_text

        return cache[url], False

    # 捕捉 requests.get 丟出的例外，如果有先前快取，則回傳快取內容，否則拋出例外
    except HTTPException as e:
        if url in cache:
            return cache[url], True
        raise e


def post(
    url: str,
    **kwargs,
) -> str:
    """
    從網址取得回應內容。Post 方法不使用快取。

    Args:
        url (str): 網址。
        **kwargs: 額外傳遞給的參數，會傳遞給 requests.get。

    Returns:
        str: 回應內容。
    """

    # 驗證網址
    try:
        url = validate_url(url)
    except ValueError as e:
        raise HTTPException(400, str(e))

    response = requests.post(url, timeout=10, **kwargs)

    status_code = response.status_code
    # 如果回應狀態碼不是 200，則拋出例外；但有可能是 2xx 範圍的狀態碼
    if status_code != 200:
        raise HTTPException(status_code, f"Request error: {status_code}")

    return response.text
