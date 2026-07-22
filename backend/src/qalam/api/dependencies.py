"""FastAPI dependency providers.

The container is built once at application startup and stored on the ASGI app
state. Handlers receive collaborators through ``Depends`` so tests can override
any of them without patching module globals — the failure mode of the previous
skeleton, which instantiated its pipeline at import time.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from qalam.application.pipeline import AnalysisPipeline
from qalam.composition.container import Container
from qalam.core.config import Settings
from qalam.plugins.base import PluginRegistry


def get_container(request: Request) -> Container:
    """Return the container attached to the running application."""
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_pipeline(container: ContainerDep) -> AnalysisPipeline:
    return container.pipeline


def get_plugins(container: ContainerDep) -> PluginRegistry:
    return container.plugins


def get_app_settings(container: ContainerDep) -> Settings:
    return container.settings


PipelineDep = Annotated[AnalysisPipeline, Depends(get_pipeline)]
PluginsDep = Annotated[PluginRegistry, Depends(get_plugins)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]
