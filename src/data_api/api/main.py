"""
Application entry point.

This module provides the uvicorn entry point for running the application.
Uses pydantic-settings for configuration.
"""

import uvicorn

from data_api.core.settings import settings

if settings.dev_mode:
    # Development
    uvicorn.run(
        app="data_api.api.api:app",
        host=settings.host,
        port=settings.port,
        log_level="debug",
        reload=True,  # reload the server every time code changes
    )
else:
    # Production
    uvicorn.run(
        app="data_api.api.api:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        workers=settings.workers,
    )
