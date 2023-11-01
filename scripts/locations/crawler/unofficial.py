# 把 map.json 的資料

import json


def mapJson():
    # "化工館": [24.796396, 120.995007],
    # 變成
    # "化工館": {latitude: 120.995007, longitude: 24.796396},
    with open("map.json", "r", encoding="UTF-8") as f:
        map_data = json.load(f)
        print(map_data)

    for key, value in map_data.items():
        map_data[key] = {"latitude": value["longitude"], "longitude": value["latitude"]}

    with open("map.json", "w", encoding="UTF-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=4)
