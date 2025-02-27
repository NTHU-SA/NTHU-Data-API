from typing import List, Optional

from pydantic import BaseModel, Field


class Contact(BaseModel):
    extension: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class Person(BaseModel):
    name: str
    title: Optional[str] = None
    extension: Optional[str] = None
    note: Optional[str] = None
    email: Optional[str] = None


class DepartmentDetails(BaseModel):
    departments: List[dict] = Field(
        default_factory=list
    )  # 這裡用 dict 簡化，完整可以再定義 DepartmentBase model
    contact: Contact = Field(default_factory=Contact)
    people: List[Person] = Field(default_factory=list)


class DepartmentBase(BaseModel):
    index: str
    name: str
    parent_name: Optional[str] = None
    url: Optional[str] = None
    details: DepartmentDetails = Field(default_factory=DepartmentDetails)


class Department(DepartmentBase):
    pass
