"""
Shared data manager instance for the application.

This module provides a global nthudata instance that can be imported
by any module without causing circular imports.
"""

import os

from src.utils.nthudata import NTHUDataManager

# Global data manager instance
# Cache expiry defaults to 5 minutes (300 seconds)
FILE_DETAILS_CACHE_EXPIRY = int(os.getenv("FILE_DETAILS_CACHE_EXPIRY", 300))

nthudata = NTHUDataManager(file_details_cache_expiry=FILE_DETAILS_CACHE_EXPIRY)
