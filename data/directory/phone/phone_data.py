# 清除 phone.json 的重複資料
import json

with open("phone.json", "r", encoding="utf-8") as f:
    data = json.load(f)

final_data = []

# 去除重複的資料
for i in data:
    if i not in final_data:
        final_data.append(i)

# 若有重複的 name，去除較後面的資料
for i in final_data:
    for j in final_data:
        if i["name"] == j["name"] and i["phone"] != j["phone"]:
            final_data.remove(j)

with open("phone.json", "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=4)
