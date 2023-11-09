import json

from phone_data_node import PhoneDataNode

with open("./original_data/dept.json", "r", encoding="utf-8") as f:
    phone_data = json.load(f)

for first_class in phone_data:
    print(
        first_class["name"], f" 共計有 {len(first_class['details']['departments'])} 個下轄機關"
    )

res = []

for first_class_index, first_class in enumerate(phone_data, start=0):
    try:
        name = first_class["name"]
    except KeyError:
        name = "N/A"

    try:
        ext = first_class["details"]["contact"]["分機"]
    except KeyError:
        ext = "N/A"

    try:
        tel = first_class["details"]["contact"]["直撥電話"]
    except KeyError:
        tel = "N/A"

    try:
        fax = first_class["details"]["contact"]["傳真電話"]
    except KeyError:
        fax = "N/A"

    try:
        email = first_class["details"]["contact"]["Email"]
    except KeyError:
        email = "N/A"

    first_class_dept = PhoneDataNode(name=name, ext=ext, tel=tel, fax=fax, email=email)

    temp = []
    for second_class in phone_data[first_class_index]["details"]["departments"]:
        try:
            name = second_class["name"]
        except KeyError:
            name = "N/A"

        try:
            ext = second_class["details"]["contact"]["分機"]
        except KeyError:
            ext = "N/A"

        try:
            tel = second_class["details"]["contact"]["直撥電話"]
        except KeyError:
            tel = "N/A"

        try:
            fax = second_class["details"]["contact"]["傳真電話"]
        except KeyError:
            fax = "N/A"

        try:
            email = second_class["details"]["contact"]["Email"]
        except KeyError:
            email = "N/A"

        second_class_dept = PhoneDataNode(
            name=name, ext=ext, tel=tel, fax=fax, email=email
        )

        second_class_dept.data["parents"].append(
            {"name": first_class_dept.data["name"], "id": first_class_dept.id}
        )

        first_class_dept.data["children"].append(
            {"name": second_class_dept.data["name"], "id": second_class_dept.id}
        )

        tempp = []
        if second_class_dept.data["name"] == "台灣聯合大學系統 校內分機免費互撥":
            for third_class in phone_data[first_class_index]["details"]["departments"][
                0
            ]["details"]["people"]:
                try:
                    name = third_class["姓名"]
                except KeyError:
                    name = "N/A"

                try:
                    ext = third_class["職稱/職責"]
                except KeyError:
                    ext = "N/A"

                try:
                    tel = third_class["details"]["contact"]["直撥電話"]
                except KeyError:
                    tel = "N/A"

                try:
                    fax = third_class["details"]["contact"]["傳真電話"]
                except KeyError:
                    fax = "N/A"

                try:
                    email = third_class["details"]["contact"]["Email"]
                except KeyError:
                    email = "N/A"

                third_class_dept = PhoneDataNode(
                    name=name, ext=ext, tel=tel, fax=fax, email=email
                )

                second_class_dept.data["children"].append(
                    {"name": third_class_dept.data["name"], "id": third_class_dept.id}
                )

                third_class_dept.data["parents"].append(
                    {"name": second_class_dept.data["name"], "id": second_class_dept.id}
                )

                tempp.append(vars(third_class_dept))

        temp.append(vars(second_class_dept))
        for i in tempp:
            temp.append(i)

    res.append(vars(first_class_dept))
    for i in temp:
        res.append(i)


with open("./phone_formatted.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=4)
