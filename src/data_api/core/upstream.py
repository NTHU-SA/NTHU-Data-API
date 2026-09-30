"""Classify expected failures at live upstream boundaries."""

import json
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
from pydantic import ValidationError

from data_api.core.exceptions import (
    UpstreamException,
    UpstreamResponseException,
    UpstreamTimeoutException,
)


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
