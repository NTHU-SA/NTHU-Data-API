from .data import Data


class Location(Data):
    def __init__(self):
        super().__init__("data/formatted/locations.json")
