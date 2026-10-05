"""Safe diagnostics and HTTP document checks for external contract checks."""

import hashlib
import json
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from data_api.data.nthudata import JsonData


@dataclass
class CheckFailure(Exception):
    target: str
    stage: str
    reason: str

    def __str__(self) -> str:
        return f"{self.target}: stage={self.stage} reason={self.reason}"


async def fetch_json(
    client: httpx.AsyncClient, url: str, target: str, checksum: str | None = None
) -> tuple[JsonData, httpx.Response]:
    try:
        response = await client.get(url)
    except httpx.TimeoutException as exc:
        raise CheckFailure(target, "http", "timeout") from exc
    except httpx.RequestError as exc:
        raise CheckFailure(target, "http", "connection/request failure") from exc
    if response.status_code != 200:
        raise CheckFailure(target, "http", f"status {response.status_code}")
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json" and not (
        content_type.startswith("application/") and content_type.endswith("+json")
    ):
        raise CheckFailure(target, "content-type", "expected application/json")
    if checksum is not None and hashlib.sha256(response.content).hexdigest() != checksum:
        raise CheckFailure(target, "checksum", "SHA-256 mismatch")
    try:
        payload = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CheckFailure(target, "json", "invalid JSON") from exc
    if not isinstance(payload, (dict, list)):
        raise CheckFailure(target, "json", "expected an object or array")
    return payload, response


def validation_reason(exc: ValidationError) -> str:
    """Report field locations and categories without copying upstream values."""
    return "; ".join(
        f"{'.'.join(map(str, error['loc'])) or '<root>'}: {error['type']}"
        for error in exc.errors(include_url=False, include_context=False, include_input=False)[:5]
    )


def report(failures: list[CheckFailure], label: str) -> int:
    if failures:
        for failure in failures:
            print(f"FAIL {label} {failure}")
        print(f"FAIL {label}: {len(failures)} external contract check(s) failed")
        return 1
    print(f"PASS {label}")
    return 0
