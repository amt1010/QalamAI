"""Builds the object graph for a running process."""

from __future__ import annotations

from dataclasses import dataclass

from qalam.adapters.unavailable import (
    UnavailableDetector,
    UnavailableKnowledgeGraph,
    UnavailableOcrEngine,
    UnavailablePreprocessor,
    UnavailableScriptClassifier,
    UnavailableTranslator,
)
from qalam.application.pipeline import AnalysisPipeline, PipelineComponents
from qalam.core.config import Settings, get_settings
from qalam.core.logging import configure_logging, get_logger
from qalam.plugins.base import PluginRegistry
from qalam.plugins.islamic_epigraphy import IslamicEpigraphyPlugin

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Container:
    """Everything a request handler may need, constructed once per process."""

    settings: Settings
    plugins: PluginRegistry
    components: PipelineComponents
    pipeline: AnalysisPipeline


def build_plugin_registry() -> PluginRegistry:
    """Register every civilization plugin this build ships with.

    Adding a civilization is one line here plus a new package under
    ``qalam.plugins`` — no change to the core, which is the plugin
    architecture's whole claim, kept honest.
    """
    return PluginRegistry((IslamicEpigraphyPlugin(),))


def build_components(settings: Settings) -> PipelineComponents:
    """Select adapters for each pipeline stage.

    Currently every stage resolves to an explicitly-unavailable adapter: no
    models have been trained or shipped yet, and the platform reports that
    rather than inventing results. As each milestone lands, the corresponding
    line here changes and nothing else does.
    """
    _ = settings  # engine selection becomes settings-driven from M3 onward
    return PipelineComponents(
        preprocessor=UnavailablePreprocessor(),
        detector=UnavailableDetector(),
        script_classifier=UnavailableScriptClassifier(),
        ocr=UnavailableOcrEngine(),
        translator=UnavailableTranslator(),
        knowledge_graph=UnavailableKnowledgeGraph(),
    )


def build_container(settings: Settings | None = None) -> Container:
    """Construct the process-wide object graph."""
    resolved = settings if settings is not None else get_settings()
    configure_logging(level=resolved.log_level, log_format=resolved.log_format)

    plugins = build_plugin_registry()
    components = build_components(resolved)
    pipeline = AnalysisPipeline(components=components, plugins=plugins, settings=resolved)

    logger.info(
        "container.built",
        environment=resolved.environment,
        plugins=list(plugins.ids()),
        default_civilization=resolved.default_civilization,
    )
    return Container(settings=resolved, plugins=plugins, components=components, pipeline=pipeline)
