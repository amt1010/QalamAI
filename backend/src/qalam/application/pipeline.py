"""The inscription analysis use case.

Composes the ports declared in :mod:`qalam.domain.ports` into one flow. Every
component is optional: the pipeline degrades stage by stage and reports what it
could not do, rather than substituting invented output.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from qalam.application.stage import run_stage
from qalam.core.config import Settings
from qalam.core.logging import get_logger
from qalam.domain.entities import (
    AnalysisRequest,
    AnalysisResult,
    DetectedRegion,
    HeritageClaim,
    ImageReference,
    OcrOutput,
    StageReport,
    StageStatus,
    TranslationOutput,
)
from qalam.domain.ports import (
    ImagePreprocessor,
    InscriptionDetector,
    KnowledgeGraphClient,
    OcrEngine,
    ScriptClassifier,
    Translator,
)
from qalam.domain.value_objects import BoundingBox, Confidence, Evidence, Script
from qalam.plugins.base import CivilizationPlugin, PluginRegistry

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineComponents:
    """The replaceable components one pipeline run may use.

    Every field defaults to ``None``, so a deployment can enable stages
    incrementally as models become available, without any code change here.
    """

    preprocessor: ImagePreprocessor | None = None
    detector: InscriptionDetector | None = None
    script_classifier: ScriptClassifier | None = None
    ocr: OcrEngine | None = None
    translator: Translator | None = None
    knowledge_graph: KnowledgeGraphClient | None = None


class AnalysisPipeline:
    """Orchestrates inscription analysis for a single image."""

    def __init__(
        self,
        *,
        components: PipelineComponents,
        plugins: PluginRegistry,
        settings: Settings,
    ) -> None:
        self._components = components
        self._plugins = plugins
        self._settings = settings

    async def run(self, request: AnalysisRequest) -> AnalysisResult:
        """Analyze one image, returning partial results where stages cannot run."""
        plugin = self._plugins.get(request.civilization or self._settings.default_civilization)
        reports: list[StageReport] = []

        log = logger.bind(request_id=str(request.request_id), civilization=plugin.id)
        log.info("analysis.started", mode=request.mode.value)

        image = await self._preprocess(request.image, reports)
        regions = await self._detect(image, reports)
        script = await self._resolve_script(request, plugin, image, regions, reports)
        ocr = await self._recognize(image, regions, script, plugin, reports)

        translation: TranslationOutput | None = None
        claims: tuple[HeritageClaim, ...] = ()
        if ocr is not None and ocr.text:
            translation = await self._translate(ocr.text, plugin, reports)
            claims = await self._gather_claims(ocr.text, script, plugin, reports)
        else:
            log.info("analysis.no_text", reason="OCR produced no transcription")

        result = AnalysisResult(
            request_id=request.request_id,
            civilization=plugin.id,
            regions=regions,
            ocr=ocr,
            translation=translation,
            claims=claims,
            stages=tuple(reports),
        )
        log.info(
            "analysis.finished",
            complete=result.is_complete,
            unavailable=list(result.unavailable_capabilities),
            claims=len(result.claims),
        )
        return result

    # -- stages --------------------------------------------------------------

    async def _preprocess(
        self, image: ImageReference, reports: list[StageReport]
    ) -> ImageReference:
        component = self._components.preprocessor
        outcome = await run_stage(
            "preprocess", component, lambda: _require(component).preprocess(image)
        )
        reports.append(outcome.report)
        # An un-enhanced image is still analyzable; fall back to the original.
        return outcome.value if outcome.value is not None else image

    async def _detect(
        self, image: ImageReference, reports: list[StageReport]
    ) -> tuple[DetectedRegion, ...]:
        component = self._components.detector
        outcome = await run_stage("detect", component, lambda: _require(component).detect(image))
        reports.append(outcome.report)
        return outcome.value if outcome.value is not None else ()

    async def _resolve_script(
        self,
        request: AnalysisRequest,
        plugin: CivilizationPlugin,
        image: ImageReference,
        regions: tuple[DetectedRegion, ...],
        reports: list[StageReport],
    ) -> Script:
        """Determine which script to route OCR with.

        Precedence: an explicit caller hint, then the classifier, then the
        plugin's default. The hint wins because a caller who knows the script —
        a museum importing an already-catalogued collection — should not be
        second-guessed by a probabilistic classifier.
        """
        if request.script_hint is not None:
            return request.script_hint

        if not regions:
            reports.append(
                StageReport(
                    name="classify_script",
                    status=StageStatus.SKIPPED,
                    duration_ms=0.0,
                    detail="No regions to classify; using the plugin's default script.",
                )
            )
            return plugin.default_script

        component = self._components.script_classifier
        region = regions[0]
        outcome = await run_stage(
            "classify_script", component, lambda: _require(component).classify(image, region)
        )
        reports.append(outcome.report)
        if outcome.value is None:
            return plugin.default_script

        script, confidence = outcome.value
        if script not in plugin.supported_scripts:
            logger.warning(
                "script.outside_plugin_scope",
                classified=script.value,
                plugin=plugin.id,
                confidence=confidence.value,
            )
            return plugin.default_script
        return script

    async def _recognize(
        self,
        image: ImageReference,
        regions: tuple[DetectedRegion, ...],
        script: Script,
        plugin: CivilizationPlugin,
        reports: list[StageReport],
    ) -> OcrOutput | None:
        component = self._components.ocr
        targets = regions if regions else (_whole_image_region(),)
        outcome = await run_stage(
            "ocr", component, lambda: _require(component).recognize(image, targets, script)
        )
        reports.append(outcome.report)
        if outcome.value is None:
            return None
        return _postprocess_ocr(outcome.value, plugin, self._settings.ocr.min_confidence)

    async def _translate(
        self, text: str, plugin: CivilizationPlugin, reports: list[StageReport]
    ) -> TranslationOutput | None:
        component = self._components.translator
        outcome = await run_stage(
            "translate",
            component,
            lambda: _require(component).translate(
                text,
                source_language=plugin.default_script.value,
                target_language=plugin.default_target_language,
            ),
        )
        reports.append(outcome.report)
        return outcome.value

    async def _gather_claims(
        self,
        text: str,
        script: Script,
        plugin: CivilizationPlugin,
        reports: list[StageReport],
    ) -> tuple[HeritageClaim, ...]:
        """Retrieve HKG evidence and turn it into attributable claims.

        Claims are built *from* evidence, never decorated with it afterwards.
        With no evidence there are no claims — the platform stays silent on
        history it cannot source. See ADR-0005.
        """
        component = self._components.knowledge_graph
        outcome = await run_stage(
            "knowledge_graph",
            component,
            lambda: _require(component).find_evidence(
                text=plugin.search_key(text), script=script, civilization=plugin.id
            ),
        )
        reports.append(outcome.report)

        evidence: tuple[Evidence, ...] = outcome.value if outcome.value is not None else ()
        return tuple(
            HeritageClaim(statement=item.note or item.citation.title, evidence=(item,))
            for item in evidence
        )


# -- helpers -----------------------------------------------------------------


def _require[T](component: T | None) -> T:
    """Narrow an optional component inside a stage action.

    ``run_stage`` only invokes the action after confirming the component is
    present and available, so this can never fire in practice; it exists so the
    stage closures type-check under mypy strict.
    """
    if component is None:  # pragma: no cover - unreachable via run_stage
        raise RuntimeError("Stage action invoked without a component")
    return component


def _whole_image_region() -> DetectedRegion:
    """A sentinel region standing for the full frame when detection did not run.

    Lets OCR still be attempted on an image the caller has already cropped to a
    single inscription — the common path for curated museum material. Adapters
    interpret the ``whole_image`` label as "ignore the box, read everything".
    """
    return DetectedRegion(
        box=BoundingBox(x=0, y=0, width=1, height=1),
        confidence=Confidence.certain(),
        label="whole_image",
    )


def _postprocess_ocr(
    output: OcrOutput, plugin: CivilizationPlugin, min_confidence: float
) -> OcrOutput:
    """Apply the plugin's canonicalization and drop low-confidence lines."""
    kept = tuple(
        replace(line, text=plugin.normalize_text(line.text))
        for line in output.lines
        if line.confidence.meets(min_confidence) and line.text.strip()
    )
    dropped = len(output.lines) - len(kept)
    if dropped:
        logger.info("ocr.lines_dropped", count=dropped, min_confidence=min_confidence)
    return replace(output, lines=kept)
