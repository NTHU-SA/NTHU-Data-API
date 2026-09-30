"""
Custom exceptions for the application.
"""

INTERNAL_ERROR_DETAIL = "Internal server error"


class DataAPIException(Exception):
    """Base exception for all Data API errors."""

    pass


class DataNotAvailableException(DataAPIException):
    """Raised when requested data is not available."""

    pass


class DataUpdateException(DataAPIException):
    """Raised when data update fails."""

    pass


class UpstreamException(DataAPIException):
    """A live upstream failure with a safe public response."""

    status_code = 502
    detail = "Upstream service unavailable"


class UpstreamTimeoutException(UpstreamException):
    """Raised when a live upstream request times out."""

    status_code = 504
    detail = "Upstream request timed out"


class UpstreamResponseException(UpstreamException):
    """Raised when a live upstream response cannot be parsed or validated."""

    detail = "Invalid response from upstream service"
