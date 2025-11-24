"""
Configuration for NTHU Data API

This module contains configuration settings including which data endpoints
should be pre-fetched at application startup.
"""

# Endpoints to pre-fetch at startup
# These are data files that are frequently accessed and should be cached
# immediately when the application starts
PREFETCH_ENDPOINTS = [
    "buses.json",
    "courses.json",
    "dining.json",
    "announcements.json",
    "announcements_list.json",
    "directory.json",
    "newsletters.json",
]
