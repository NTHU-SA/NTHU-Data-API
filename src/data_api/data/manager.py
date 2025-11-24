"""
Shared data manager instance for the application.

This module provides a global nthudata instance that can be imported
by any module without causing circular imports.
"""

from data_api.core.settings import settings
from data_api.data import NTHUDataManager

# Global data manager instance
nthudata = NTHUDataManager(file_details_cache_expiry=settings.file_details_cache_expiry)
