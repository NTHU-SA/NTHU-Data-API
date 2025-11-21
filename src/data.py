"""
Shared data manager instance for the application.

This module provides a global nthudata instance that can be imported
by any module without causing circular imports.
"""

from src import config
from src.utils.nthudata import NTHUDataManager

# Global data manager instance
nthudata = NTHUDataManager(file_details_cache_expiry=config.FILE_DETAILS_CACHE_EXPIRY)
