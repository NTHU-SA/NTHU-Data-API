# Data Manager Architecture

This document describes the refactored data fetching architecture for the NTHU Data API.

## Overview

The data fetching logic has been refactored to provide better separation of concerns, improved error handling, and configurable pre-fetching capabilities. The new architecture consists of several components:

## Components

### 1. DataFetcher (`src/utils/data_manager.py`)

**Purpose:** Handles HTTP fetching of JSON data.

**Key Features:**
- Uses httpx AsyncClient for async HTTP requests
- Handles HTTP errors and JSON parsing errors gracefully
- Returns `None` on errors for consistent error handling

**Example:**
```python
fetcher = DataFetcher("https://data.nthusa.tw")
data = await fetcher.fetch_json("https://data.nthusa.tw/buses.json")
```

### 2. FileDetailsManager (`src/utils/data_manager.py`)

**Purpose:** Manages `file_details.json` for tracking commit hashes.

**Key Features:**
- Caches `file_details.json` with configurable expiry (default: 5 minutes)
- Formats the nested structure into a flat list
- Provides commit hash lookup by endpoint name

**Example:**
```python
manager = FileDetailsManager(fetcher, "https://data.nthusa.tw/file_details.json")
file_details = await manager.get_file_details()
commit_hash = manager.get_commit_hash("/buses.json", file_details)
```

### 3. DataCache (`src/utils/data_manager.py`)

**Purpose:** Manages in-memory cache for data with commit hash validation.

**Key Features:**
- Stores data with associated commit hashes
- Validates cache based on commit hash comparison
- Supports clearing individual keys or entire cache

**Example:**
```python
cache = DataCache()
cache.set("buses.json", {"data": "value"}, "commit_hash_123")
is_valid = cache.is_valid("buses.json", "commit_hash_123")
```

### 4. NTHUDataManager (`src/utils/data_manager.py`)

**Purpose:** Main data manager providing a unified interface for data fetching and caching.

**Key Features:**
- Combines all components into a single interface
- Automatic cache validation using commit hashes
- Pre-fetch capability for multiple endpoints
- Graceful error handling with fallback to stale cache

**Example:**
```python
manager = NTHUDataManager()

# Get single endpoint
commit_hash, data = await manager.get("buses.json")

# Pre-fetch multiple endpoints
results = await manager.prefetch(["buses.json", "courses.json"])
```

### 5. Configuration (`src/config.py`)

**Purpose:** Centralized configuration for pre-fetch settings.

**Key Features:**
- `PREFETCH_ENDPOINTS`: List of endpoints to pre-fetch at startup
- `FILE_DETAILS_CACHE_EXPIRY`: Cache expiry time for file_details.json

**Example:**
```python
PREFETCH_ENDPOINTS = [
    "buses.json",
    "courses.json",
    "dining.json",
    # ... add more endpoints as needed
]

FILE_DETAILS_CACHE_EXPIRY = 60 * 5  # 5 minutes
```

## Application Startup

The application uses a centralized lifespan manager in `src/api/routers/__init__.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup: Pre-fetch configured endpoints
    results = await data_manager.prefetch(config.PREFETCH_ENDPOINTS)
    
    # Initialize module-specific data processors
    await courses.courses.update_data()
    await buses.buses.update_data()
    
    yield
    
    # Shutdown: cleanup if needed
```

## Backward Compatibility

The original `src/utils/nthudata.py` module is maintained for backward compatibility:

- All existing code using `nthudata.get()` continues to work
- Internally delegates to the new `NTHUDataManager`
- Provides the same API interface

## Error Handling

All components handle errors gracefully:

1. **Network errors**: Return `None` and log error messages
2. **JSON parsing errors**: Return `None` and log error messages
3. **Missing data**: Return `None` with warning messages
4. **Stale cache fallback**: If fresh data fetch fails, returns stale cache if available

The data processors (courses, buses) check for `None` returns and skip updates:

```python
async def update_data(self) -> None:
    result = await nthudata.get("courses.json")
    if result is None:
        print("Warning: Could not fetch courses.json, keeping existing data")
        return
    
    self.last_commit_hash, self.course_data = result
    # ... process data
```

## Testing

Tests are provided in `tests/test_data_manager.py`:

- `TestDataFetcher`: Tests for HTTP fetching
- `TestFileDetailsManager`: Tests for file details management
- `TestDataCache`: Tests for cache operations
- `TestNTHUDataManager`: Integration tests for the main manager

Run tests with:
```bash
python3 -m pytest tests/test_data_manager.py -v
```

## Migration Guide

### For New Code

Use the new `NTHUDataManager` directly:

```python
from src.utils.data_manager import NTHUDataManager

manager = NTHUDataManager()
commit_hash, data = await manager.get("buses.json")
```

### For Existing Code

No changes needed! The code continues to work:

```python
from src.utils import nthudata

commit_hash, data = await nthudata.get("buses.json")
```

## Benefits

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Improved Error Handling**: Consistent error handling throughout the stack
3. **Configurable Pre-fetching**: Easy to configure which endpoints to pre-fetch
4. **Better Testability**: Each component can be tested independently
5. **Backward Compatible**: No breaking changes to existing code
6. **Cleaner Code**: Simpler logic with better readability
7. **Flexible**: Easy to extend with new features

## Future Enhancements

Potential future improvements:

1. Add metrics/monitoring for cache hits/misses
2. Support for different cache backends (Redis, etc.)
3. Configurable cache expiry per endpoint
4. Automatic retry logic for failed fetches
5. Background refresh of stale cache
6. Webhook support for data update notifications
