"""API discovery metadata."""

from pydantic import BaseModel


class MetaResponse(BaseModel):
    name: str
    version: str
    docs: str
    openapi: str
    mcp: str
