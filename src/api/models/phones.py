from .data import Data


class Phone(Data):
    def __init__(self):
        super().__init__("data/formatted/phone.json")


if __name__ == "__main__":
    phone = Phone()
    query = "學科所"
    print(query)
    print(phone.fuzzy_search(query))
