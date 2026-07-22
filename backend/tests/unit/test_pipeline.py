"""Pipeline orchestration: degradation, routing, and post-processing.

The central property under test is that the pipeline never fabricates. Where a
stage cannot run, the result reports the gap and downstream stages do not
invent a substitute.
"""

from __future__ import annotations

import pytest

from qalam.application.pipeline import AnalysisPipeline, PipelineComponents
from qalam.core.config import OcrSettings, Settings
from qalam.domain.entities import (
    AnalysisMode,
    AnalysisRequest,
    ImageReference,
    StageStatus,
)
from qalam.domain.value_objects import Script
from qalam.plugins.base import PluginRegistry
from tests.conftest import (
    FakeDetector,
    FakeKnowledgeGraph,
    FakeOcrEngine,
    FakePreprocessor,
    FakeScriptClassifier,
    FakeTranslator,
)

pytestmark = pytest.mark.unit


def _request(**kwargs: object) -> AnalysisRequest:
    return AnalysisRequest(image=ImageReference(uri="file://sample.jpg"), **kwargs)  # type: ignore[arg-type]


def _stage(result: object, name: str) -> object:
    stages = result.stages  # type: ignore[attr-defined]
    return next(stage for stage in stages if stage.name == name)


class TestHappyPath:
    async def test_runs_every_stage_and_produces_a_reading(
        self, pipeline: AnalysisPipeline
    ) -> None:
        result = await pipeline.run(_request())
        assert result.is_complete
        assert result.ocr is not None
        assert result.translation is not None
        assert result.civilization == "islamic_epigraphy"

    async def test_applies_plugin_canonicalization_to_recognized_text(
        self, pipeline: AnalysisPipeline
    ) -> None:
        """The kashida in the fake engine's output must be gone."""
        result = await pipeline.run(_request())
        assert result.ocr is not None
        assert "ـ" not in result.ocr.text
        assert "الرحمن" in result.ocr.text

    async def test_drops_lines_below_the_confidence_threshold(
        self, pipeline: AnalysisPipeline
    ) -> None:
        result = await pipeline.run(_request())
        assert result.ocr is not None
        assert len(result.ocr.lines) == 2  # the 0.12-confidence fragment is discarded
        assert all(line.confidence.meets(0.5) for line in result.ocr.lines)

    async def test_claims_are_built_from_evidence(self, pipeline: AnalysisPipeline) -> None:
        result = await pipeline.run(_request())
        assert result.claims
        assert all(claim.evidence for claim in result.claims)


class TestDegradation:
    async def test_missing_ocr_yields_no_reading_and_no_fabrication(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        pipeline = AnalysisPipeline(
            components=PipelineComponents(detector=FakeDetector()),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert result.ocr is None
        assert result.translation is None
        assert result.claims == ()
        assert not result.is_complete

    async def test_unavailable_component_is_reported_not_skipped(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        pipeline = AnalysisPipeline(
            components=PipelineComponents(ocr=FakeOcrEngine(available=False)),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert "ocr" in result.unavailable_capabilities
        assert _stage(result, "ocr").status is StageStatus.UNAVAILABLE  # type: ignore[attr-defined]

    async def test_absent_component_is_skipped_not_unavailable(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        """'Not deployed' and 'deployed but broken' must stay distinguishable."""
        pipeline = AnalysisPipeline(
            components=PipelineComponents(ocr=FakeOcrEngine()),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert _stage(result, "preprocess").status is StageStatus.SKIPPED  # type: ignore[attr-defined]

    async def test_a_crashing_stage_is_contained_and_reported(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        pipeline = AnalysisPipeline(
            components=PipelineComponents(detector=FakeDetector(), ocr=FakeOcrEngine(raises=True)),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert result.ocr is None
        ocr_stage = _stage(result, "ocr")
        assert ocr_stage.status is StageStatus.FAILED  # type: ignore[attr-defined]
        assert "simulated engine crash" in ocr_stage.detail  # type: ignore[attr-defined]

    async def test_preprocessing_failure_falls_back_to_the_original_image(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        pipeline = AnalysisPipeline(
            components=PipelineComponents(
                preprocessor=FakePreprocessor(available=False), ocr=FakeOcrEngine()
            ),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert result.ocr is not None  # analysis proceeds on the unenhanced image

    async def test_ocr_still_attempted_when_detection_is_unavailable(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        """Curated, already-cropped images must remain analyzable."""
        ocr = FakeOcrEngine()
        pipeline = AnalysisPipeline(
            components=PipelineComponents(detector=FakeDetector(available=False), ocr=ocr),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert "recognize" in ocr.calls
        assert result.ocr is not None


class TestScriptRouting:
    async def test_caller_hint_wins_over_the_classifier(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        classifier = FakeScriptClassifier()
        pipeline = AnalysisPipeline(
            components=PipelineComponents(
                detector=FakeDetector(), script_classifier=classifier, ocr=FakeOcrEngine()
            ),
            plugins=plugins,
            settings=settings,
        )
        await pipeline.run(_request(script_hint=Script.PERSIAN))
        assert classifier.calls == []  # classification skipped entirely

    async def test_classification_outside_plugin_scope_falls_back_to_default(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        pipeline = AnalysisPipeline(
            components=PipelineComponents(
                detector=FakeDetector(),
                script_classifier=FakeScriptClassifier(script=Script.CUNEIFORM),
                ocr=FakeOcrEngine(),
            ),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert result.ocr is not None  # did not route to an engine that cannot help

    async def test_classification_skipped_when_no_regions_found(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        classifier = FakeScriptClassifier()
        pipeline = AnalysisPipeline(
            components=PipelineComponents(script_classifier=classifier, ocr=FakeOcrEngine()),
            plugins=plugins,
            settings=settings,
        )
        result = await pipeline.run(_request())
        assert classifier.calls == []
        assert _stage(result, "classify_script").status is StageStatus.SKIPPED  # type: ignore[attr-defined]


class TestConfiguration:
    async def test_confidence_threshold_is_settings_driven(self, plugins: PluginRegistry) -> None:
        strict = Settings(
            environment="test", log_level="WARNING", ocr=OcrSettings(min_confidence=0.9)
        )
        pipeline = AnalysisPipeline(
            components=PipelineComponents(ocr=FakeOcrEngine()), plugins=plugins, settings=strict
        )
        result = await pipeline.run(_request())
        assert result.ocr is not None
        assert len(result.ocr.lines) == 1  # only the 0.93 line survives

    async def test_unknown_civilization_is_rejected(self, pipeline: AnalysisPipeline) -> None:
        from qalam.core.errors import PluginNotFoundError

        with pytest.raises(PluginNotFoundError):
            await pipeline.run(_request(civilization="atlantean"))

    async def test_mode_does_not_change_conclusions(self, pipeline: AnalysisPipeline) -> None:
        """Audience affects disclosure only — never what the platform concluded."""
        tourist = await pipeline.run(_request(mode=AnalysisMode.TOURIST))
        research = await pipeline.run(_request(mode=AnalysisMode.RESEARCH))
        assert tourist.ocr is not None and research.ocr is not None
        assert tourist.ocr.text == research.ocr.text
        assert len(tourist.claims) == len(research.claims)


class TestObservability:
    async def test_every_stage_reports_timing_and_implementation(
        self, pipeline: AnalysisPipeline
    ) -> None:
        result = await pipeline.run(_request())
        assert result.stages
        for stage in result.stages:
            assert stage.duration_ms >= 0.0
            if stage.status is StageStatus.COMPLETED:
                assert stage.implementation_id is not None

    async def test_knowledge_graph_receives_the_folded_search_key(
        self, plugins: PluginRegistry, settings: Settings
    ) -> None:
        kg = FakeKnowledgeGraph()
        pipeline = AnalysisPipeline(
            components=PipelineComponents(
                ocr=FakeOcrEngine(), translator=FakeTranslator(), knowledge_graph=kg
            ),
            plugins=plugins,
            settings=settings,
        )
        await pipeline.run(_request())
        assert kg.calls == ["find_evidence"]
