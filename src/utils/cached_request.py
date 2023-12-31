from urllib.parse import urlparse, urlunparse

import requests
from cachetools import TTLCache
from fastapi import HTTPException

ttl_cache = TTLCache(maxsize=1024, ttl=60 * 60)


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
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Invalid URL")
    # 只允許 http 或 https 協議
    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError("Invalid URL scheme")
    # 只允許 nthu.edu.tw 結尾的網域
    if not parsed_url.netloc.endswith("nthu.edu.tw"):
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
    if url in ttl_cache:
        del ttl_cache[url]


def get(url: str, cache=True, update=False, auto_headers=True, **kwargs) -> str:
    """
    從網址取得回應內容。
    Args:
        url (str): 網址。
        cache (bool): 是否使用快取。
        update (bool): 是否更新快取。
        **kwargs: 額外傳遞給的參數，會傳遞給 requests.get。
    """

    # 驗證網址
    try:
        url = validate_url(url)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if update and url in ttl_cache:
        del ttl_cache[url]
    if cache and url in ttl_cache:
        return ttl_cache[url]
    if auto_headers is True:
        headers = generate_headers(url)
    else:
        headers = None
    response = requests.get(url, headers, timeout=10, **kwargs)
    status_code = response.status_code
    if status_code != 200:
        raise HTTPException(status_code, f"Request error: {status_code}")
    response_text = response.text
    if cache:
        ttl_cache[url] = response_text
    return response_text


def post(url: str, cache=True, update=False, **kwargs) -> str:
    """
    從網址取得回應內容。
    """
    if update and url in ttl_cache:
        del ttl_cache[url]
    if cache and url in ttl_cache:
        return ttl_cache[url]
    response = requests.post(url, timeout=10, **kwargs)
    status_code = response.status_code
    if status_code != 200:
        raise HTTPException(status_code, f"Request error: {status_code}")
    response_text = response.text
    if cache:
        ttl_cache[url] = response_text
    return response_text
