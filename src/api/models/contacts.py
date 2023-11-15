from .data import Data


class Contact(Data):
    def __init__(self):
        super().__init__("data/formatted/contacts.json")
