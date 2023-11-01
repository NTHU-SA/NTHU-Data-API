from ..data_node import DataNode


class PhoneDataNode(DataNode):
    def __init__(self, name: str, ext: str, tel: str, fax: str, email: str) -> None:
        super().__init__()
        self.data = {
            "name": name,
            "ext": ext,
            "tel": tel,
            "fax": fax,
            "email": email,
            "parents": [],
            "children": [],
        }
