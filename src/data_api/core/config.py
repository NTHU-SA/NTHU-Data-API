"""
Configuration for NTHU Data API

This module contains configuration settings including which data endpoints
should be pre-fetched at application startup.
"""

# Pre-fetch published datasets used by REST/MCP so readiness needs no user traffic.
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
    "libraries/rss.json",
    "libraries/calendars.json",
]
