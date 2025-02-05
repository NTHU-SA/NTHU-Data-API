from ..data_node import DataNode


class LocationDataNode(DataNode):
    def __init__(self, name: str, name_en: str, latitude: any, longitude: any) -> None:
        super().__init__()
        self.data = {
            "name": name,
            "name_en": name_en,
            "latitude": latitude,
            "longitude": longitude,
        }
