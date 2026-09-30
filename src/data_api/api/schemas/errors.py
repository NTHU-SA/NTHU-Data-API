"""Public error responses for live integrations."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


LIVE_ERROR_RESPONSES = {
    500: {"model": ErrorResponse, "description": "Unexpected internal error"},
    502: {"model": ErrorResponse, "description": "Upstream unavailable or invalid response"},
    504: {"model": ErrorResponse, "description": "Upstream request timed out"},
}
