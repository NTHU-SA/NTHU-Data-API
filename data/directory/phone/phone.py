from loguru import logger

# 提取 dept.json 裡面的資料
import json

with open("dept.json", "r", encoding="utf-8") as f:
    data = json.load(f)

phone_list = []

for i in data:
    try:
        name = i["name"]
        phone = i["details"]["contact"]["直撥電話"]
        temp_phone = {"name": name, "phone": phone}
        phone_list.append(temp_phone)
        logger.info(temp_phone)
    except KeyError:
        pass

    for j in i["details"]["departments"]:
        print(j)
        try:
            contact = j["details"]["contact"]["直撥電話"]
            temp_phone = {"name": j["name"], "phone": contact}
            phone_list.append(temp_phone)
            logger.info(temp_phone)
        except KeyError:
            pass

with open("phone.json", "w", encoding="utf-8") as f:
    json.dump(phone_list, f, ensure_ascii=False, indent=4)
