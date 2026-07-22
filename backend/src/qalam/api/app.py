"""ASGI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from qalam.api.errors import register_error_handlers
from qalam.api.v1.routes import router as v1_router
from qalam.composition.container import build_container
from qalam.core.config import Settings
from qalam.core.logging import get_logger

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI application.

    A factory rather than a module-level singleton: tests, benchmarks, and
    future entry points each need an app with their own configuration, and an
    import-time global makes that impossible without monkeypatching.
    """
    container = build_container(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container
        logger.info(
            "app.startup",
            environment=container.settings.environment,
            version=container.settings.api_version,
        )
        yield
        logger.info("app.shutdown")

    app = FastAPI(
        title=container.settings.api_title,
        version=container.settings.api_version,
        description=(
            "QalamAI Heritage Intelligence Platform. Every historical claim "
            "returned by this API carries supporting evidence; claims that "
            "cannot be sourced are not returned."
        ),
        lifespan=lifespan,
    )

    # Also set outside the lifespan so that a TestClient used without entering
    # its context manager still resolves dependencies.
    app.state.container = container

    register_error_handlers(app)
    app.include_router(v1_router, prefix=container.settings.api_prefix)
    return app


app = create_app()
"""Default application instance for ``uvicorn qalam.api.app:app``."""
