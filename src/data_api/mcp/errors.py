"""Safe tool errors for live integrations."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastmcp.exceptions import ToolError

from data_api.core.exceptions import INTERNAL_ERROR_DETAIL, UpstreamException

logger = logging.getLogger(__name__)


@contextmanager
def live_tool_errors() -> Iterator[None]:
    try:
        yield
    except UpstreamException as exc:
        logger.warning("Live MCP upstream request failed", exc_info=exc)
        raise ToolError(exc.detail) from exc
    except Exception as exc:
        logger.error("Unexpected live MCP tool failure", exc_info=exc)
        raise ToolError(INTERNAL_ERROR_DETAIL) from exc
