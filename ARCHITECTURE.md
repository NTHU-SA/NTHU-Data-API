# NTHU Data API - Layered Architecture

This document describes the new layered architecture implemented for the NTHU Data API.

## Architecture Overview

The project follows clean architecture principles with clear separation of concerns:

```
src/data_api/
├── api/              # API Layer - HTTP concerns
│   ├── routers/      # FastAPI route handlers
│   ├── schemas/      # Pydantic request/response models
│   ├── deps/         # FastAPI dependencies
│   ├── api.py        # FastAPI app creation
│   └── main.py       # Application entry point
│
├── core/             # Core Layer - Configuration and constants
│   ├── config.py     # Application configuration
│   ├── constants.py  # Application-wide constants
│   └── exceptions.py # Custom exceptions
│
├── domain/           # Domain Layer - Business logic
│   ├── buses/
│   │   ├── models.py    # Domain models (pure Python)
│   │   ├── services.py  # Business logic
│   │   ├── enums.py     # Domain enumerations
│   │   └── adapters.py  # Domain ↔ Schema conversion
│   ├── announcements/
│   ├── dining/
│   └── ...
│
├── data/             # Data Layer - Data fetching and caching
│   ├── nthudata.py   # Data manager
│   └── manager.py    # Global instance
│
└── utils/            # Utilities
    └── schema.py     # Schema helpers
```

## Layer Responsibilities

### API Layer (`api/`)
- **Purpose**: Handle HTTP requests and responses
- **Dependencies**: Can import from domain, data, and core layers
- **Rules**:
  - No business logic in routers
  - Only handle HTTP concerns (request validation, response formatting, headers)
  - Delegate all business logic to domain services
  - Use Pydantic schemas for validation

### Domain Layer (`domain/`)
- **Purpose**: Contain business logic and domain models
- **Dependencies**: Only core layer (no FastAPI, no Pydantic)
- **Rules**:
  - Pure Python models (dataclasses, regular classes)
  - Business logic in services
  - Independent of frameworks
  - Easily testable without HTTP layer

### Data Layer (`data/`)
- **Purpose**: Handle data fetching and caching
- **Dependencies**: Core layer
- **Rules**:
  - Abstract data sources
  - Provide clean interfaces
  - Handle caching and retries

### Core Layer (`core/`)
- **Purpose**: Application configuration and shared utilities
- **Dependencies**: None (foundational layer)
- **Rules**:
  - No business logic
  - Configuration and constants only
  - Custom exceptions

## Module Structure Pattern

Each domain module follows this pattern:

```python
domain/{module}/
  models.py      # Domain models (if complex business entities exist)
  services.py    # Business logic (required)
  enums.py       # Domain enumerations (if needed)
  adapters.py    # Conversion functions (if needed)
  __init__.py    # Module exports

api/schemas/{module}.py    # Pydantic models
api/routers/{module}.py    # FastAPI endpoints
```

### Example: Buses Module

```python
# domain/buses/models.py - Pure Python
@dataclass
class Stop:
    name: str
    name_en: str
    latitude: str
    longitude: str

# domain/buses/services.py - Business Logic
class BusesService:
    async def update_data(self) -> None:
        # Fetch and process data
        
    def get_main_data(self) -> dict:
        # Return processed data

buses_service = BusesService()

# api/schemas/buses.py - Pydantic Models
class BusInfo(BaseModel):
    direction: str
    duration: str

# api/routers/buses.py - HTTP Handlers
@router.get("/main", response_model=BusMainData)
async def get_main_campus_bus_data():
    await buses_service.update_data()
    return buses_service.get_main_data()
```

## Running the Application

### New Structure (Recommended)
```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/NTHU-Data-API/src

# Run with Python module
python -m data_api.api.main

# Or with uvicorn directly
uvicorn data_api.api.api:app --reload
```

### Old Structure (Legacy, still works)
```bash
python main.py  # Uses src:app (old structure)
```

## Migration Status

### Completed (8/9 modules)
- ✅ Buses - Full refactor with domain models
- ✅ Announcements
- ✅ Dining - With domain enums
- ✅ Energy
- ✅ Libraries
- ✅ Locations
- ✅ Newsletters
- ✅ Departments

### Remaining
- ⏳ Courses - Complex module with Processor class

## Benefits

1. **Separation of Concerns**: Each layer has a clear responsibility
2. **Testability**: Business logic can be tested without HTTP layer
3. **Maintainability**: Clear structure makes code easy to find and modify
4. **Framework Independence**: Domain logic doesn't depend on FastAPI
5. **Scalability**: Easy to add new modules following the same pattern

## Testing

### Domain Layer Tests
```python
# Test business logic without HTTP
from data_api.domain.buses import services

async def test_bus_service():
    await services.buses_service.update_data()
    data = services.buses_service.get_main_data()
    assert data is not None
```

### API Layer Tests
```python
# Test HTTP endpoints
from fastapi.testclient import TestClient
from data_api.api.api import app

client = TestClient(app)

def test_buses_endpoint():
    response = client.get("/buses/main")
    assert response.status_code == 200
```

## Adding a New Module

1. Create domain structure:
```bash
mkdir -p src/data_api/domain/mymodule
touch src/data_api/domain/mymodule/{__init__.py,services.py}
```

2. Implement service:
```python
# src/data_api/domain/mymodule/services.py
from data_api.data.manager import nthudata

class MyModuleService:
    async def get_data(self):
        result = await nthudata.get("mydata.json")
        return result

mymodule_service = MyModuleService()
```

3. Create schema:
```python
# src/data_api/api/schemas/mymodule.py
from pydantic import BaseModel, Field

class MyData(BaseModel):
    field: str = Field(..., description="Description")
```

4. Create router:
```python
# src/data_api/api/routers/mymodule.py
from fastapi import APIRouter
from data_api.api.schemas import mymodule as schemas
from data_api.domain.mymodule import services

router = APIRouter()

@router.get("/", response_model=schemas.MyData)
async def get_mydata():
    return await services.mymodule_service.get_data()
```

5. Register router in `api/api.py`:
```python
from data_api.api.routers import mymodule
app.include_router(mymodule.router, prefix="/mymodule", tags=["MyModule"])
```

## Code Style Guidelines

1. **Naming Conventions**:
   - Services: `{module}_service` (e.g., `buses_service`)
   - Domain models: PascalCase (e.g., `BusStop`)
   - Functions: snake_case (e.g., `get_main_data`)

2. **Import Organization**:
   ```python
   # Standard library
   import asyncio
   from datetime import datetime
   
   # Third party
   from fastapi import APIRouter
   from pydantic import BaseModel
   
   # Local application
   from data_api.core import config
   from data_api.domain.buses import services
   ```

3. **Type Hints**: Always use type hints
4. **Docstrings**: Add docstrings to public functions and classes
5. **Error Handling**: Use appropriate HTTP exceptions in routers

## Migration Notes

### For Developers
- Old code in `src/api/` still exists but is deprecated
- New code should use `src/data_api/` structure
- Tests need to be updated to import from new structure
- Old entry point (`src:app`) vs new (`data_api.api.api:app`)

### Breaking Changes
- Import paths have changed
- Service instances are now global (e.g., `buses_service`)
- Enums moved from schemas to domain layer

### Backwards Compatibility
- Old structure still works for gradual migration
- Can run both old and new simultaneously during transition
- Tests should be updated module by module
