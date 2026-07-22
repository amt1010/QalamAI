"""Structured logging setup.

Observability is a stated platform principle. Every log line is a structured
event with a stable name and typed fields, so that pipeline stages can be
measured in aggregate ("p95 latency of ocr.completed by engine") rather than
grepped.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from qalam.core.config import LogFormat


def configure_logging(*, level: str = "INFO", log_format: LogFormat = "console") -> None:
    """Configure structlog and the stdlib root logger.

    Idempotent: safe to call from both the ASGI startup hook and test fixtures.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # ConsoleRenderer formats exceptions itself and warns if handed an already
    # formatted traceback, so format_exc_info is only added for JSON output.
    renderer: Any
    if log_format == "json":
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger for ``name``."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
