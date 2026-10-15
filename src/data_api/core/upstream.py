"""Classify expected failures at live upstream boundaries."""

import json
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from ssl import SSLContext

import httpx
from pydantic import ValidationError

from data_api.core.exceptions import (
    UpstreamException,
    UpstreamResponseException,
    UpstreamTimeoutException,
)


@asynccontextmanager
async def live_client(
    client: httpx.AsyncClient | None, *, verify: SSLContext | bool = True
) -> AsyncIterator[httpx.AsyncClient]:
    """Borrow a runtime client, or own one for a standalone service call."""
    if client is not None:
        yield client
    else:
        async with httpx.AsyncClient(verify=verify) as owned:
            yield owned


@contextmanager
def upstream_errors() -> Iterator[None]:
    try:
        yield
    except httpx.TimeoutException as exc:
        raise UpstreamTimeoutException("Live upstream request timed out") from exc
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise UpstreamException("Live upstream request failed") from exc
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        raise UpstreamResponseException("Live upstream response could not be parsed") from exc
