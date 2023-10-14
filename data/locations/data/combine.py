import json


# 合併 main_zh 和 nanda_zh 的資料，並檢查是否有重複的資料
def combine_json():
    with open("main_zh.json", "r", encoding="UTF-8") as f:
        main_data = json.load(f)
    with open("nanda_zh.json", "r", encoding="UTF-8") as f:
        nanda_data = json.load(f)
    # 檢查是否有重複的資料
    for key, value in nanda_data.items():
        if key not in main_data:
            main_data[key] = value
        elif key in main_data:
            print("重複資料: ", key, value)
            print("使用 main 的資料: " + key, main_data[key])
    # 將資料存入 json 檔案
    with open("map_zh.json", "w", encoding="UTF-8") as f:
        json.dump(main_data, f, ensure_ascii=False, indent=4)


# 合併 main_en 和 nanda_en 的資料，並檢查是否有重複的資料
def combine_json_en():
    with open("main_en.json", "r", encoding="UTF-8") as f:
        main_data = json.load(f)
    with open("nanda_en.json", "r", encoding="UTF-8") as f:
        nanda_data = json.load(f)
    # 檢查是否有重複的資料
    for key, value in nanda_data.items():
        if key not in main_data:
            main_data[key] = value
        elif key in main_data:
            print("重複資料: ", key, value)
            print("使用 main 的資料: " + key, main_data[key])
    # 將資料存入 json 檔案
    with open("map_en.json", "w", encoding="UTF-8") as f:
        json.dump(main_data, f, ensure_ascii=False, indent=4)


combine_json_en()
