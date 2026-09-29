"""
Configuration for NTHU Data API

This module contains configuration settings including which data endpoints
should be pre-fetched at application startup.
"""

# Pre-fetch every published dataset so readiness can succeed without user traffic.
PREFETCH_ENDPOINTS = [
    "buses.json",
    "courses.json",
    "calendars.json",
    "dining.json",
    "announcements.json",
    "announcements_list.json",
    "directory.json",
    "newsletters.json",
    "maps.json",
    "libraries.json",
    "libraries/rss.json",
    "libraries/calendars.json",
]
