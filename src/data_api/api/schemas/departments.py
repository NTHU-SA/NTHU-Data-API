"""Departments API schemas."""

from typing import Optional

from pydantic import BaseModel, BeforeValidator, Field
from pydantic.networks import HttpUrl
from typing_extensions import Annotated

from data_api.utils.schema import url_corrector


class DepartmentPerson(BaseModel):
    name: str = Field(..., description="姓名")
    title: Optional[str] = Field(..., description="職稱")
    extension: Optional[str] = Field(..., description="分機")
    note: Optional[str] = Field(None, description="備註")
    email: Optional[str] = Field(..., description="電子郵件")


class DepartmentContact(BaseModel):
    extension: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = None


class DepartmentDetails(BaseModel):
    departments: list[dict] = Field(default_factory=list)
    contact: DepartmentContact = Field(default_factory=DepartmentContact)
    people: list[DepartmentPerson] = Field(default_factory=list)


class Department(BaseModel):
    index: str = Field(..., description="系所代碼")
    name: str = Field(..., description="系所名稱")
    parent_name: Optional[str] = Field(None, description="上層系所名稱")
    url: Optional[Annotated[HttpUrl, BeforeValidator(url_corrector)]] = Field(
        None, description="系所網站"
    )
    details: DepartmentDetails = Field(default_factory=DepartmentDetails)
