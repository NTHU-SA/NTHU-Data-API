from .data import Data


class Location(Data):
    def __init__(self):
        super().__init__("data/formatted/locations.json")


if __name__ == "__main__":
    location = Location()
    query = "East gate"
    print(query)
    print(location.fuzzy_search("東門"))
