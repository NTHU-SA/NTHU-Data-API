# 爬取 https://tel.net.nthu.edu.tw/nthusearch/dept.php 的資料

base_url = "https://tel.net.nthu.edu.tw/nthusearch/"

import json
import re

import bs4
import requests
from cachetools import TTLCache, cached
from loguru import logger


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


# 取得所有系所的網址
def get_all_dept_url():
    response_text, response_code = get_response(
        "https://tel.net.nthu.edu.tw/nthusearch/index.php"
    )
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

            # 將網址加入 base_url
            url = base_url + url
            print(url, name)
            departments.append({"name": name, "url": url})

    with open("departments.json", "w", encoding="UTF-8") as f:
        json.dump(departments, f, ensure_ascii=False, indent=4)
    return departments


# 取得系所的資料
def get_dept_details(url):
    # https://tel.net.nthu.edu.tw/nthusearch/dept.php?departments=43
    response_text, response_code = get_response(url)
    text = response_text

    # 使用 bs4 解析 response
    soup = bs4.BeautifulSoup(text, "html.parser")

    def get_dept_departments():
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
            # 將網址加入 base_url
            url = base_url + url
            departments.append({"name": name, "url": url})
        return departments

    try:
        departments = get_dept_departments()
    except Exception as e:
        logger.error(f"{url} 的 departments 失效了，錯誤為 {e}")
        departments = []

    def get_dept_contact():
        # 取得 div story_max 的內容
        story_max = soup.select_one("div.story_max")
        # 分開取得 story_max 的兩個 table
        story_max = story_max.select("table")

        # 處理第一個 table
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
        story_max1 = story_max[0].select("tr")
        for i in story_max1:
            # 取得第一個 table 的子項目的子項目
            # <td>分機</td><td>62222、62223</td>
            story_max1_1 = i.select("td")
            # 取得第一個 table 的子項目的子項目的名稱和資料
            name = story_max1_1[0].text.strip()
            data = story_max1_1[1].text.strip().replace(" ", "")
            if data == "":
                link = story_max1_1[1].select_one("a")
                if link is not None:
                    data = link.get("href").replace("mailto:", "")
                else:
                    data = "N/A"
            if name == "" or data == "":
                continue
            contact[name] = data

        return contact

    try:
        contact = get_dept_contact()
    except Exception as e:
        logger.error(f"{url} 的 contact 失效了，錯誤為 {e}")
        contact = {}

    def get_dept_people():
        # 取得 div story_max 的內容
        story_max = soup.select_one("div.story_max")
        # 分開取得 story_max 的兩個 table
        story_max = story_max.select("table")

        # 處理第二個 table
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
        <tr bgcolor="#EEEEEE"><td width="18%">吳尚衡</td>
        <td>專案助理</td><td>62222</td><td align=center></td>
        <td align=center><a href="mailto:shanghengwu@mx.nthu.edu.tw"><img src="./image/mail.jpg" border=0 alt='寄信'></a></td>
        </tr>
        <tr>
        <td width="18%">林怡君</td>
        <td>音樂藝術企劃</td><td>62377</td><td align=center></td>
        <td align=center><a href="mailto:ichunlin@mx.nthu.edu.tw"><img src="./image/mail.jpg" border=0 alt='寄信'></a></td>
        </tr>
        <tr bgcolor="#EEEEEE"><td width="18%">林甫珊</td>
        <td>視覺藝術企劃</td><td>62497</td><td align=center></td>
        <td align=center><a href="mailto:fslin@mx.nthu.edu.tw"><img src="./image/mail.jpg" border=0 alt='寄信'></a></td>
        </tr>
        </table>
        """

        # 取得第二個 table 的子項目
        story_max2 = story_max[1].select("tr")
        story_max2_1 = story_max2[0].select("td")
        people_col = []
        # 透過第二個 table 的第一個子項目的子項目建立欄位名稱
        for i in story_max2_1:
            people_col.append(i.text.strip().replace("\u3000", ""))

        story_max2 = story_max2[1:]
        people = []

        for i in story_max2:
            # 取得第二個 table 的子項目的子項目
            # <td>簡禎富</td>
            story_max2_1 = i.select("td")
            people_temp = {}
            col = 0
            for j in story_max2_1:
                data = j.text.strip()
                # 取得第二個 table 的子項目的子項目的名稱和資料
                if data == "":
                    link = j.select_one("a")
                    if link is not None:
                        data = link.get("href").replace("mailto:", "")
                    else:
                        data = "N/A"
                people_temp[people_col[col]] = data
                col += 1
            people.append(people_temp)

        return people

    try:
        people = get_dept_people()
    except Exception as e:
        logger.error(f"{url} 的 people 失效了，錯誤為 {e}")
        people = []

    result = {"departments": departments, "contact": contact, "people": people}

    return result


import os
import random
import string


def get_newname(o_filename):
    """
    filename file3.txt => file3
    extension file3.txt => .txt
    new_filename file3-[a-z]{5}.txt
    """
    size = 5
    filename = os.path.splitext(o_filename)[0]
    extension = os.path.splitext(o_filename)[1]
    random_string = "".join(random.choice(string.ascii_letters) for x in range(5))
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
def get_dept_departments():
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


def get_dept_departments_dir():
    files = os.listdir("dept")
    print(files)
    start_index = files.index("研究發展處")
    print(start_index)


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
    data = get_dept_details(
        "https://tel.net.nthu.edu.tw/nthusearch/dept.php?departments=43"
    )
    print(data)
