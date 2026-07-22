"""Shared fixtures and test doubles.

The fakes here are *test doubles*, not placeholders: they exist so pipeline and
API behaviour can be exercised deterministically without model weights. They
live under ``tests/`` and are never importable from production code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from qalam.application.pipeline import AnalysisPipeline, PipelineComponents
from qalam.core.config import KnowledgeGraphSettings, OcrSettings, Settings
from qalam.domain.entities import (
    DetectedRegion,
    ImageReference,
    OcrOutput,
    RecognizedLine,
    TranslationOutput,
)
from qalam.domain.value_objects import (
    BoundingBox,
    Citation,
    Confidence,
    Evidence,
    EvidenceKind,
    Script,
)
from qalam.plugins.base import PluginRegistry
from qalam.plugins.islamic_epigraphy import IslamicEpigraphyPlugin


@dataclass
class FakeCapability:
    """Base for doubles, with controllable availability."""

    available: bool = True
    calls: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"fake:{type(self).__name__}"

    @property
    def is_available(self) -> bool:
        return self.available

    @property
    def availability_reason(self) -> str:
        return "fake double" if self.available else "deliberately disabled for this test"


@dataclass
class FakePreprocessor(FakeCapability):
    async def preprocess(self, image: ImageReference) -> ImageReference:
        self.calls.append("preprocess")
        return ImageReference(uri=f"{image.uri}#enhanced", content_type=image.content_type)


@dataclass
class FakeDetector(FakeCapability):
    regions: tuple[DetectedRegion, ...] = (
        DetectedRegion(
            box=BoundingBox(x=10, y=20, width=200, height=50), confidence=Confidence(0.88)
        ),
    )

    async def detect(self, image: ImageReference) -> tuple[DetectedRegion, ...]:
        self.calls.append("detect")
        return self.regions


@dataclass
class FakeScriptClassifier(FakeCapability):
    script: Script = Script.ARABIC
    confidence: Confidence = field(default_factory=lambda: Confidence(0.95))

    async def classify(
        self, image: ImageReference, region: DetectedRegion
    ) -> tuple[Script, Confidence]:
        self.calls.append("classify")
        return self.script, self.confidence


@dataclass
class FakeOcrEngine(FakeCapability):
    """Returns fixed Arabic text with deliberate artefacts for the plugin to clean."""

    lines: tuple[RecognizedLine, ...] = (
        # Contains a kashida and a low-confidence fragment that must be dropped.
        RecognizedLine(text="بِسْمِ ٱللَّهِ", confidence=Confidence(0.93), script=Script.ARABIC),
        RecognizedLine(text="الرحـــمن", confidence=Confidence(0.81), script=Script.ARABIC),
        RecognizedLine(text="؟؟؟", confidence=Confidence(0.12), script=Script.ARABIC),
    )
    raises: bool = False

    @property
    def supported_scripts(self) -> frozenset[Script]:
        return frozenset({Script.ARABIC})

    async def recognize(
        self, image: ImageReference, regions: tuple[DetectedRegion, ...], script: Script
    ) -> OcrOutput:
        self.calls.append("recognize")
        if self.raises:
            raise RuntimeError("simulated engine crash")
        return OcrOutput(lines=self.lines, engine_id=self.id)


@dataclass
class FakeTranslator(FakeCapability):
    async def translate(
        self, text: str, *, source_language: str, target_language: str
    ) -> TranslationOutput:
        self.calls.append("translate")
        return TranslationOutput(
            text=f"[{target_language}] {text}",
            source_language=source_language,
            target_language=target_language,
            engine_id=self.id,
            confidence=Confidence(0.75),
        )


@dataclass
class FakeKnowledgeGraph(FakeCapability):
    evidence: tuple[Evidence, ...] = (
        Evidence(
            citation=Citation(
                title="Quran 1:1",
                identifier="quran:1:1",
                kind=EvidenceKind.PRIMARY_SOURCE,
                locator="Surah al-Fatiha, ayah 1",
            ),
            confidence=Confidence(0.97),
            note="The inscription opens with the Basmala.",
        ),
    )

    async def find_evidence(
        self, *, text: str, script: Script, civilization: str, limit: int = 10
    ) -> tuple[Evidence, ...]:
        self.calls.append("find_evidence")
        return self.evidence


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    """Deterministic test configuration, isolated from the ambient environment."""
    return Settings(
        environment="test",
        log_level="WARNING",
        ocr=OcrSettings(min_confidence=0.5),
        knowledge_graph=KnowledgeGraphSettings(),
    )


@pytest.fixture
def plugins() -> PluginRegistry:
    return PluginRegistry((IslamicEpigraphyPlugin(),))


@pytest.fixture
def full_components() -> PipelineComponents:
    """Every stage wired to a working double."""
    return PipelineComponents(
        preprocessor=FakePreprocessor(),
        detector=FakeDetector(),
        script_classifier=FakeScriptClassifier(),
        ocr=FakeOcrEngine(),
        translator=FakeTranslator(),
        knowledge_graph=FakeKnowledgeGraph(),
    )


@pytest.fixture
def pipeline(
    full_components: PipelineComponents, plugins: PluginRegistry, settings: Settings
) -> AnalysisPipeline:
    return AnalysisPipeline(components=full_components, plugins=plugins, settings=settings)
