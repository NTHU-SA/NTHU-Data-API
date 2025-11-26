"""Tests for utils module."""

from data_api.utils.schema import url_corrector


class TestUrlCorrector:
    """Tests for url_corrector function."""

    async def test_url_corrector_none_input(self):
        """Test that None input returns None."""
        result = url_corrector(None)
        assert result is None

    async def test_url_corrector_double_slash_prefix(self):
        """Test URL starting with //."""
        result = url_corrector("//example.com/path")
        assert result == "https://example.com/path"

    async def test_url_corrector_valid_http(self):
        """Test valid http URL is unchanged."""
        url = "http://example.com/path"
        result = url_corrector(url)
        assert result == url

    async def test_url_corrector_valid_https(self):
        """Test valid https URL is unchanged."""
        url = "https://example.com/path"
        result = url_corrector(url)
        assert result == url

    async def test_url_corrector_invalid_protocol(self):
        """Test URL with invalid protocol gets corrected."""
        result = url_corrector("ftp://example.com/path")
        assert result == "https://example.com/path"

    async def test_url_corrector_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = url_corrector("  https://example.com/path  ")
        assert result == "https://example.com/path"

    async def test_url_corrector_no_protocol(self):
        """Test URL without protocol is unchanged."""
        url = "example.com/path"
        result = url_corrector(url)
        assert result == url
