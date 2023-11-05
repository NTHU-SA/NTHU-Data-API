import requests
from cachetools import TTLCache

ttl_cache = TTLCache(maxsize=1024, ttl=60 * 60)


def delete(url: str) -> None:
    if url in ttl_cache:
        del ttl_cache[url]


def get(url: str, cache=True, update=False) -> str:
    """
    從網址取得回應內容。
    Args:
        url (str): 網址。
        cache (bool): 是否使用快取。
        update (bool): 是否更新快取。
    """
    if update and url in ttl_cache:
        del ttl_cache[url]
    if cache and url in ttl_cache:
        return ttl_cache[url]
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-CN;q=0.5",
        "dnt": "1",
        "referer": url,
        "sec-ch-ua": "'Chromium';v='119', 'Microsoft Edge';v='119', 'Not:A-Brand';v='24'",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "Android",
        "sec-fetch-dest": "script",
        "sec-fetch-mode": "no-cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36 Edg/112.0.1722.48",
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Request error: {response.status_code}")
    response_text = response.text
    if cache:
        ttl_cache[url] = response_text
    return response_text
