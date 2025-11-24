"""Departments API schemas."""
from pydantic import BaseModel, Field

class DepartmentPerson(BaseModel):
    name: str = Field(..., description="姓名")
    title: str = Field(..., description="職稱")
    phone: str = Field(..., description="電話")
    email: str = Field(..., description="電子郵件")

class Department(BaseModel):
    name: str = Field(..., description="部門名稱")
    people: list[DepartmentPerson] = Field(..., description="部門人員")
