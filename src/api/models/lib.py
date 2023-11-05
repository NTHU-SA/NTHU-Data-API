import re
import requests
import xmltodict


def get_response(url):
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-CN;q=0.5",
        "dnt": "1",
        "referer": "https://www.lib.nthu.edu.tw/",
        "sec-ch-ua": "'Chromium';v='112', 'Microsoft Edge';v='112', 'Not:A-Brand';v='99'",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "Android",
        "sec-fetch-dest": "script",
        "sec-fetch-mode": "no-cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36 Edg/112.0.1722.48",
    }
    response = requests.get(url, headers=headers)
    response_text = response.text
    response_code = response.status_code
    return response_text, response_code


def get_people_in_library():
    url = "https://adage.lib.nthu.edu.tw/nthu/number_of_Lib/data_mainlib.js"
    text, code = get_response(url)
    # 使用正規表達式從 document.write() 中提取數字
    num_match = re.search(r"\d+", text)
    if num_match:
        num = num_match.group()
    else:
        num = "Error"
        code = 404
    result = {"peoples": num}
    return result, code


def get_number_of_goods():
    url = "https://adage.lib.nthu.edu.tw/goods/Public/number_of_goods_mix.js"
    text, code = get_response(url)
    # 使用正規表達式從 result 中提取變量和值
    variables = re.findall(r'var\s+(\w+)\s*=\s*(\d+|"[^"]*");', text)
    # 將變量和值存儲在字典中
    result = {}
    for variable in variables:
        key, value = variable
        if value.isdigit():
            value = value
        else:
            value = value.strip('"')
        result[key] = value
    if result:
        code = 200
    return result, code


def get_opening_hours(library):
    # mainlib
    # hslib
    # nandalib
    url = f"https://www.lib.nthu.edu.tw/bulletin/OpeningHours/{library}.js"
    text, code = get_response(url)
    # 使用正規表達式從 response 中提取日期和時間
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
    result = {
        "library": library,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
    }
    return result, code


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
    response_code = response.status_code
    data = response.json()

    return data, response_code


def get_rss_data(url):
    rss_news = (
        "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_news.xml"  # 最新消息 RSS
    )
    rss_eresources = (
        "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_eresources.xml"  # 電子資源 RSS
    )
    rss_exhibit = (
        "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_exhibit.xml"  # 展覽及活動 RSS
    )
    rss_branches = "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_branches.xml"  # 南大與人社分館 RSS
    url = f"https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_{url}.xml"
    text, code = get_response(url)
    xml_string = text.replace("<br />", " ")
    dict = xmltodict.parse(xml_string)
    dict = dict["rss"]["channel"]
    return dict, code
