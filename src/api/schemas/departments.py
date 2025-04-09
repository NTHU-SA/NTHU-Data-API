from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

from src.utils.schema import url_corrector


class DepartmentContact(BaseModel):
    extension: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = None


class DepartmentPerson(BaseModel):
    name: str
    title: Optional[str] = None
    extension: Optional[str] = None
    note: Optional[str] = None
    email: Optional[str] = None


class DepartmentDetails(BaseModel):
    departments: list[dict] = Field(default_factory=list)
    contact: DepartmentContact = Field(default_factory=DepartmentContact)
    people: list[DepartmentPerson] = Field(default_factory=list)


class DepartmentBase(BaseModel):
    index: str
    name: str
    parent_name: Optional[str] = None
    url: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = None
    details: DepartmentDetails = Field(default_factory=DepartmentDetails)


class Department(DepartmentBase):
    pass
