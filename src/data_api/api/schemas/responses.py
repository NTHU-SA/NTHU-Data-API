"""Snapshot response metadata shared by canonical and compatibility routes."""

from data_api.api.schemas.errors import ErrorResponse

DATA_VERSION_HEADERS = {
    "X-Data-Commit-Hash": {
        "description": "Opaque source version; omitted when the version is unknown",
        "schema": {"type": "string"},
    },
}
COUNT_HEADERS = {
    **DATA_VERSION_HEADERS,
    "X-Total-Count": {
        "description": "Number of matching records before pagination",
        "schema": {"type": "integer", "minimum": 0},
        "required": True,
    },
}
SNAPSHOT_RESPONSES = {
    200: {"headers": DATA_VERSION_HEADERS},
    503: {"model": ErrorResponse, "description": "No usable dataset snapshot"},
}
COUNTED_SNAPSHOT_RESPONSES = {
    **SNAPSHOT_RESPONSES,
    200: {"headers": COUNT_HEADERS},
}
