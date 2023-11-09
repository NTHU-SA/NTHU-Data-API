from .data import Data


class Contact(Data):
    def __init__(self):
        super().__init__("data/formatted/contacts.json")


if __name__ == "__main__":
    contact = Contact()
    query = "學科所"
    print(query)
    print(contact.fuzzy_search(query))
