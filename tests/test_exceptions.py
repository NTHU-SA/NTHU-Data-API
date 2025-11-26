"""Tests for core exceptions module."""

import pytest

from data_api.core.exceptions import (
    DataAPIException,
    DataNotAvailableException,
    DataUpdateException,
)


class TestDataAPIException:
    """Tests for DataAPIException."""

    async def test_base_exception(self):
        """Test DataAPIException can be raised and caught."""
        with pytest.raises(DataAPIException) as exc_info:
            raise DataAPIException("Test error")
        assert "Test error" in str(exc_info.value)

    async def test_base_exception_inheritance(self):
        """Test DataAPIException inherits from Exception."""
        exc = DataAPIException("Test")
        assert isinstance(exc, Exception)


class TestDataNotAvailableException:
    """Tests for DataNotAvailableException."""

    async def test_data_not_available(self):
        """Test DataNotAvailableException can be raised."""
        with pytest.raises(DataNotAvailableException) as exc_info:
            raise DataNotAvailableException("Data unavailable")
        assert "Data unavailable" in str(exc_info.value)

    async def test_inheritance(self):
        """Test it inherits from DataAPIException."""
        exc = DataNotAvailableException("Test")
        assert isinstance(exc, DataAPIException)


class TestDataUpdateException:
    """Tests for DataUpdateException."""

    async def test_data_update_exception(self):
        """Test DataUpdateException can be raised."""
        with pytest.raises(DataUpdateException) as exc_info:
            raise DataUpdateException("Update failed")
        assert "Update failed" in str(exc_info.value)

    async def test_inheritance(self):
        """Test it inherits from DataAPIException."""
        exc = DataUpdateException("Test")
        assert isinstance(exc, DataAPIException)


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    async def test_catch_specific_with_base(self):
        """Test catching specific exceptions with base exception."""
        try:
            raise DataNotAvailableException("Test")
        except DataAPIException as e:
            assert isinstance(e, DataNotAvailableException)

    async def test_catch_data_update_with_base(self):
        """Test catching DataUpdateException with base exception."""
        try:
            raise DataUpdateException("Test")
        except DataAPIException as e:
            assert isinstance(e, DataUpdateException)
