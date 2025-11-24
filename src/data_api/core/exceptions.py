"""
Custom exceptions for the application.
"""


class DataAPIException(Exception):
    """Base exception for all Data API errors."""

    pass


class DataNotAvailableException(DataAPIException):
    """Raised when requested data is not available."""

    pass


class DataUpdateException(DataAPIException):
    """Raised when data update fails."""

    pass
