import re
import requests
import xmltodict

from src.utils import cached_request


def get_people_in_library():
    url = "https://adage.lib.nthu.edu.tw/nthu/number_of_Lib/data_mainlib.js"
    text = cached_request.get(url)
    # 使用正規表達式從 document.write() 中提取數字
    num_match = re.search(r"\d+", text)
    if num_match:
        peoples = num_match.group()
    else:
        peoples = None
    return peoples


def get_number_of_goods() -> dict:
    url = "https://adage.lib.nthu.edu.tw/goods/Public/number_of_goods_mix.js"
    text = cached_request.get(url)
    # 使用正規表達式從 text 中提取變量和值
    variables = re.findall(r'var\s+(\w+)\s*=\s*(\d+|"[^"]*");', text)
    # 將變量和值存儲在字典中
    data = {}
    for variable in variables:
        key, value = variable
        if value.isdigit():
            value = value
        else:
            value = value.strip('"')
        data[key] = value
    return data


def get_opening_hours(library):
    # mainlib
    # hslib
    # nandalib
    url = f"https://www.lib.nthu.edu.tw/bulletin/OpeningHours/{library}.js"
    text = cached_request.get(url)
    # 使用正規表達式從 text 中提取日期和時間
    match = re.search(
        r"(\d{4}-\d{2}-\d{2}\s+\([\w]+\))<br />(\d{2}:\d{2})-(\d{2}:\d{2})", text
    )
    if match:
        date = match.group(1)
        start_time = match.group(2)
        end_time = match.group(3)
    else:
        code = 404
        date, start_time, end_time = "", "", ""
    # 將日期和時間存儲在字典中
    data = {
        "library": library,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
    }
    return data


def get_space_data():
    # URL of the page to be scraped
    # https://libsms.lib.nthu.edu.tw/build/
    url = "https://libsms.lib.nthu.edu.tw/RWDAPI_New/GetDevUseStatus.aspx"  # replace with the actual URL of the page
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": "https://libsms.lib.nthu.edu.tw/build/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
    }

    payload = {
        "t": "1",
    }

    # send a GET request to the URL and get the HTML content
    response = requests.get(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code {response.status_code}")
    data = response.json()
    return data
