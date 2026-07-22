"""Translation of domain errors into HTTP responses.

Handlers are registered centrally so that no route needs try/except and every
error reaches the client in one shape: ``{code, message, details}``.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from qalam.core.errors import QalamError
from qalam.core.logging import get_logger

logger = get_logger(__name__)


async def qalam_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render a :class:`QalamError` using its declared code and status."""
    assert isinstance(exc, QalamError)
    logger.warning(
        "request.rejected",
        code=exc.code,
        path=request.url.path,
        detail=exc.message,
    )
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render an unexpected exception without leaking internals.

    The message is deliberately generic: stack traces and exception text can
    disclose file paths, configuration, and dependency versions. The detail
    goes to the structured log, where operators can find it.
    """
    logger.exception("request.failed", path=request.url.path, error=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "code": "internal_error",
            "message": "An unexpected error occurred.",
            "details": {},
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach the platform's exception handlers to ``app``."""
    app.add_exception_handler(QalamError, qalam_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
