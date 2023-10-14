# 將目錄裡面的 json 與 json 合併
# example:
# 教務處.json
# {
# "departments": [
#     {
#         "name": "綜合教務組",
#         "url": "https://tel.net.nthu.edu.tw/nthusearch/dept.php?departments=1701"
#     },
#     ]}
# 教務處/綜合教務組.json
# {...}
# result:
# 教務處.json
# {
# "departments": [
#     {"name": "綜合教務組", "url": "https://tel.net.nthu.edu.tw/nthusearch/dept.php?departments=1701", "details": {...}},
#     ]}

import json
import os


def combine_file():
    files = os.listdir("dept")
    # 移除不為 json 結尾的檔案
    files = [i for i in files if i.endswith(".json")]
    # 開啟 json 檔案
    for i in files:
        with open(f"dept/{i}", "r", encoding="utf-8") as f:
            data = json.load(f)
        # 取得子系所的資料夾名稱
        dept_name = os.path.splitext(i)[0]
        # 取得子系所的資料夾路徑
        dept_path = f"dept/{dept_name}"
        # 取得子系所的資料夾中的所有檔案
        dept_files = os.listdir(dept_path)
        # 移除不為 json 結尾的檔案
        dept_files = [i for i in dept_files if i.endswith(".json")]
        # 開啟子系所的 json 檔案
        for j in dept_files:
            with open(f"{dept_path}/{j}", "r", encoding="utf-8") as f:
                dept_data = json.load(f)
            # 將子系所的資料加入到父系所的資料中
            for k in data["departments"]:
                if k["name"] == j.split(".")[0]:
                    k["details"] = dept_data
        # 將父系所的資料存入 json 檔案
        with open(f"combined/{i}", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


# 把所有的 json 檔案合併成一個 json 檔案
def combine_json():
    files = os.listdir("combined")
    # 搜尋是否有 JSON 結尾對應的資料夾
    files = [i for i in files if i.endswith(".json")]
    final_data = []
    # 開啟 json 檔案
    for i in files:
        with open(f"combined/{i}", "r", encoding="utf-8") as f:
            data = json.load(f)
        # 將資料加入到 final_data 中的 key["file_name"] 中
        dept_name = os.path.splitext(i)[0]
        temp_data = {"name": dept_name, "details": data}
        final_data.append(temp_data)

    # 將 final_data 存入 json 檔案
    with open("dept.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)


# 把 contact.json 裡面的資料合併到 dept.json 裡面
def combine_contact():
    with open("departments.json", "r", encoding="utf-8") as f:
        contact_data = json.load(f)
    with open("dept.json", "r", encoding="utf-8") as f:
        dept_data = json.load(f)
    for i in contact_data:
        for j in dept_data:
            if i["name"] == j["name"]:
                j["url"] = i["url"]

    with open("dept.json", "w", encoding="utf-8") as f:
        json.dump(dept_data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    combine_file()
