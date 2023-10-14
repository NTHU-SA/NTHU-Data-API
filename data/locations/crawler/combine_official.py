# 把 _official 和 _unofficial 的資料合併
# 若有重複的資料，則使用 _official 的資料

import json


def main():
    with open("main_official.json", "r", encoding="UTF-8") as f:
        map_data_official = json.load(f)

    with open("main_unofficial.json", "r", encoding="UTF-8") as f:
        map_data_unofficial = json.load(f)

    map_data = map_data_official.copy()

    for key, value in map_data_unofficial.items():
        if key not in map_data:
            map_data[key] = value
        elif key in map_data:
            print("重複資料: ", key, value)
            print("使用 official 的資料: " + key, map_data[key])

    with open("map_main.json", "w", encoding="UTF-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=4)


def nanda():
    with open("nanda_official.json", "r", encoding="UTF-8") as f:
        map_data_official = json.load(f)

    with open("nanda_unofficial.json", "r", encoding="UTF-8") as f:
        map_data_unofficial = json.load(f)

    map_data = map_data_official.copy()

    for key, value in map_data_unofficial.items():
        if key not in map_data:
            map_data[key] = value
        elif key in map_data:
            print("重複資料: ", key, value)
            print("使用 official 的資料: " + key, map_data[key])

    with open("map_nanda.json", "w", encoding="UTF-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=4)
