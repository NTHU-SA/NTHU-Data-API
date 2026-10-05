"""Reusable public error responses."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str
    input: Any = None
    ctx: dict[str, Any] | None = None


class ValidationErrorResponse(BaseModel):
    detail: str | list[ValidationIssue]


VALIDATION_ERROR_RESPONSES = {
    422: {
        "model": ValidationErrorResponse,
        "description": "Invalid request parameter, body, or regular expression",
    },
}


LIVE_ERROR_RESPONSES = {
    500: {"model": ErrorResponse, "description": "Unexpected internal error"},
    502: {"model": ErrorResponse, "description": "Upstream unavailable or invalid response"},
    504: {"model": ErrorResponse, "description": "Upstream request timed out"},
}
