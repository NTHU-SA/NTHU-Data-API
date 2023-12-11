import json
import os
import random
import re
import string

import bs4
import requests
from cachetools import TTLCache, cached
from loguru import logger

# 爬取 https://tel.net.nthu.edu.tw/nthusearch/dept.php 的資料
BASE_URL = "https://tel.net.nthu.edu.tw/nthusearch/"


@cached(cache=TTLCache(maxsize=1024, ttl=60 * 60 * 24))
def get_response(url):
    logger.info(f"取得 {url} 的 response")
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-CN;q=0.5",
        "dnt": "1",
        "referer": url,
        "host": "tel.net.nthu.edu.tw",
        "sec-ch-ua": "'Chromium';v='112', 'Microsoft Edge';v='112', 'Not:A-Brand';v='99'",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "Android",
        "sec-fetch-dest": "script",
        "sec-fetch-mode": "no-cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36 Edg/112.0.1722.48",
    }
    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    response_text = response.text
    response_code = response.status_code
    return response_text, response_code


def get_all_dept_url():
    """
    取得所有系所的網址
    """
    response_text, _ = get_response("https://tel.net.nthu.edu.tw/nthusearch/index.php")
    text = response_text
    text = text.split("\n")

    departments = []

    for i in text:
        # 使用正規表達式從 response 中提取所有系所的網址和名稱
        # <li><a href="dept.php?departments=03">副校長室</a></li>
        match = re.search(r'<li><a href="(.*?)">(.*?)</a></li>', i)
        if match:
            url = match.group(1)
            name = match.group(2)
            url = BASE_URL + url
            print(url, name)
            departments.append({"name": name, "url": url})

    with open("departments.json", "w", encoding="UTF-8") as f:
        json.dump(departments, f, ensure_ascii=False, indent=4)

    return departments


def get_dept_departments(soup):
    """
    取得系所的子系所的名稱和網址
    """
    departments = []
    # 取得 div story_left 的內容
    story_left = soup.select_one("div.story_left")
    # 取得 story_left 的子項目
    # <a href="dept.php?departments=7505">音樂學系</a>
    story_left = story_left.select("a")
    # 取得系所的子項目的網址和名稱
    for i in story_left:
        url = i.get("href")
        name = i.text
        url = BASE_URL + url
        departments.append({"name": name, "url": url})
    return departments


def get_dept_contact(first_story_max):
    """
    取得系所的聯絡資訊
    """

    """
    <table width="100%"  border="0" cellspacing="0" cellpadepartmentsing="0">
    <tr><td>分機</td><td>62222、62223</td></tr>
    <tr><td>直撥電話</td><td>03- 5162222</td></tr>
    <tr><td>傳真電話</td><td>03- 5726819 </td></tr>
    <tr><td>Email</td><td><a href=mailto:cac@my.nthu.edu.tw><img src="./image/mail.jpg" border=0 alt='寄信'></a></td></tr>
    <tr><td>網頁</td><td><a href=https://cac.site.nthu.edu.tw/app/index.php><img src="./image/home.png" border=0 alt='網頁'></a></td></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td></tr>    </table>
    """
    contact = {}
    # 取得第一個 table 的子項目
    for i in first_story_max:
        # 取得第一個 table 的子項目的子項目
        # <td>分機</td><td>62222、62223</td>
        first_story_max_td = i.select("td")
        # 取得第一個 table 的子項目的子項目的名稱和資料
        name = first_story_max_td[0].text.strip()
        data = first_story_max_td[1].text.strip().replace(" ", "")
        if link := first_story_max_td[1].select_one("a"):
            if link is None:
                data = "N/A"
            else:
                data = link.get("href").replace("mailto:", "")
        if name and data:
            contact[name] = data

    return contact


def get_dept_people(second_story_max):
    """
    取得系所的人員資訊
    """

    """
    <table width="100%"  border="0" cellspacing="2" cellpadepartmentsing="2">
    <tr>
    <td width="18%"><b>姓　名</b></td>
    <td width="37%"><b>職稱/職責</b></td>
    <td width="23%"><b>分機</b></td>
    <td width="18%"><b>備註</b></td>
    <td width="4%"><b>Email</b></td>
    </tr>
    <tr>
    <td>簡禎富</td>
    <td>副校長兼總中心主任</td><td>62503</td><td align=center></td>
    <td align=center><a href="mailto:cfchien@mx.nthu.edu.tw"><img src="./image/mail.jpg" border=0 alt='寄信'></a></td>
    </tr>
    </table>
    """

    if len(second_story_max) == 0:
        return None

    # 透過第二個 table 的第一個子項目的子項目建立欄位名稱
    second_story_max_1_td = second_story_max[0].select("td")
    people_col = []
    for i in second_story_max_1_td:
        people_col.append(i.text.strip().replace("\u3000", ""))

    people = []
    for i in second_story_max:
        # 取得第二個 table 的子項目的子項目
        # <td>簡禎富</td>
        second_story_max_td = i.select("td")
        people_temp = {}
        col = 0
        for j in second_story_max_td:
            data = j.text.strip()
            # 取得第二個 table 的子項目的子項目的名稱和資料
            if link := j.select_one("a"):
                data = (
                    "N/A" if link is None else link.get("href").replace("mailto:", "")
                )

            people_temp[people_col[col]] = data
            col += 1
        people.append(people_temp)

    return people


# 取得系所的資料
def get_dept_details(url):
    # https://tel.net.nthu.edu.tw/nthusearch/dept.php?departments=43
    response_text, _ = get_response(url)
    text = response_text
    # 使用 bs4 解析 response
    soup = bs4.BeautifulSoup(text, "html.parser")
    # 取得系所的子系所的名稱和網址
    try:
        departments = get_dept_departments(soup)
    except Exception as e:
        logger.error(f"{url} 的 departments 失效了，錯誤為 {e}")
        departments = []
    # 處理頁面的兩個 table
    # 取得 div story_max 的內容
    story_max = soup.select_one("div.story_max")
    if story_max is None:
        return {"departments": departments, "contact": {}, "people": []}
    # 分開取得 story_max 的兩個 table
    story_max = story_max.select("table")
    # 取得系所的聯絡資訊
    contact = get_dept_contact(story_max[0].select("tr")) or {}
    # 取得系所的人員資訊
    people = get_dept_people(story_max[1].select("tr")) or []
    result = {"departments": departments, "contact": contact, "people": people}
    return result


def get_newname(o_filename):
    """
    filename file3.txt => file3
    extension file3.txt => .txt
    new_filename file3-[a-z]{5}.txt
    """
    filename = os.path.splitext(o_filename)[0]
    extension = os.path.splitext(o_filename)[1]
    random_string = "".join(random.choice(string.ascii_letters) for _ in range(5))
    new_filename = f"{filename}-{random_string}{extension}"
    return new_filename


# 連續爬取所有系所的資料
def get_all_dept_details():
    departments = get_all_dept_url()
    for i in departments:
        result = get_dept_details(i["url"])
        print(result)
        filename = f"{i['name']}.json"
        if os.path.isfile(f"dept/{filename}"):
            filename = f"{i['name']}{result['people'][0]['姓名']}.json"
        with open(f"dept/{filename}", "w", encoding="UTF-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)


# 從 dept 資料夾中取得所有系所的資料
def get_all_dept_details_from_file():
    files = os.listdir("dept")
    for i in files:
        with open(f"dept/{i}", "r", encoding="UTF-8") as f:
            result = json.load(f)
        print(result)


# 從系所的資料中取得子系所的名稱和網址，並爬取並存至系所資料夾中
def get_dept_departments_to_dir():
    files = os.listdir("dept")
    files = [i for i in files if i.endswith(".json")]
    for i in files:
        with open(f"dept/{i}", "r", encoding="UTF-8") as f:
            result = json.load(f)
        departments = result["departments"]
        dept_name = i
        # 建立系所資料夾
        # 移除 json 副檔名
        dept_name = os.path.splitext(dept_name)[0]
        if not os.path.isdir(f"dept/{dept_name}"):
            os.mkdir(f"dept/{dept_name}")
        for i in departments:
            result = get_dept_details(i["url"])
            print(result)
            filename = f"{i['name']}.json".replace("/", "&")
            if os.path.isfile(f"dept/{dept_name}/{filename}"):
                filename = get_newname(filename)
            with open(f"dept/{dept_name}/{filename}", "w", encoding="UTF-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=4)


# 撈取指定系所的資料
def get_selected_dept_departments(dept_name):
    with open(f"dept/{dept_name}.json", "r", encoding="UTF-8") as f:
        result = json.load(f)
    departments = result["departments"]
    # 建立系所資料夾
    # 移除 json 副檔名
    dept_name = os.path.splitext(dept_name)[0]
    if not os.path.isdir(f"dept/{dept_name}"):
        os.mkdir(f"dept/{dept_name}")
    for i in departments:
        result = get_dept_details(i["url"])
        print(result)
        filename = f"{i['name']}.json"
        if os.path.isfile(f"dept/{dept_name}/{filename}"):
            filename = get_newname(filename)
        with open(f"dept/{dept_name}/{filename}", "w", encoding="UTF-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)


# 撈取沒有資料的系所的資料
def get_nodata_dept_departments():
    files = os.listdir("dept")
    # 搜尋是否有 JSON 結尾對應的資料夾
    files = [i for i in files if i.endswith(".json")]
    # 如果沒有資料夾，則執行 get_selected_dept_departments()
    for i in files:
        dept_name = os.path.splitext(i)[0]
        if not os.path.isdir(f"dept/{dept_name}"):
            get_selected_dept_departments(dept_name)


if __name__ == "__main__":
    data = get_dept_details("https://tel.net.nthu.edu.tw/nthusearch/dept.php?dd=86")
    print(data)
