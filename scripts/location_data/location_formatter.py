import json
from location_data_node import LocationDataNode

zh_location = dict()
en_location = dict()


def en_name(latitude, longitude):
    for i in en_location.items():
        name_en = i[0]
        latitude_en = str(i[1]["latitude"])
        longitude_en = str(i[1]["longitude"])

        if latitude == latitude_en and longitude == longitude_en:
            return name_en

    return "N/A"


with open("./original_data/zh.json", "r", encoding="utf-8") as f:
    zh_location = json.load(f)
with open("./original_data/en.json", "r", encoding="utf-8") as f:
    en_location = json.load(f)

res = []

for i in zh_location.items():
    name = i[0]
    latitude = str(i[1]["latitude"])
    longitude = str(i[1]["longitude"])

    location = LocationDataNode(
        name=name,
        name_en=en_name(latitude, longitude),
        latitude=latitude,
        longitude=longitude,
    )

    res.append(vars(location))

with open("../location_formatted.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=4)
