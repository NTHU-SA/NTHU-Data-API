"""Safe internal errors inside the normal HTTP middleware stack."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException

from data_api.core.exceptions import (
    INTERNAL_ERROR_DETAIL,
    DataNotAvailableException,
    UpstreamException,
)

logger = logging.getLogger(__name__)


@contextmanager
def service_errors() -> Iterator[None]:
    try:
        yield
    except DataNotAvailableException, UpstreamException, HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected request failure", exc_info=exc)
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_DETAIL) from exc
