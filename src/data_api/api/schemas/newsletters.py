"""Newsletters API schemas."""

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field, HttpUrl

from data_api.utils.schema import url_corrector


class NewsletterName(str, Enum):
    """Newsletter names."""
    國立清華大學學生會電子報 = "國立清華大學學生會電子報"
    國立清華大學電子報 = "國立清華大學電子報"


class NewsletterIssue(BaseModel):
    """Newsletter issue."""
    title: str = Field(..., description="標題")
    url: Annotated[HttpUrl, BeforeValidator(url_corrector)] = Field(..., description="連結")


class NewsletterInfo(BaseModel):
    """Newsletter information."""
    name: str = Field(..., description="電子報名稱")
    issues: list[NewsletterIssue] = Field(..., description="電子報期數列表")
