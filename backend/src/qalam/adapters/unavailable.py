"""Adapters that honestly declare a capability is not yet implemented.

These are **not** placeholders or stubs that return fake results. They are the
production behaviour for a deployment in which a given model has not been
trained, shipped, or configured: the platform states precisely which capability
is missing and why, and returns no inscription reading at all.

The alternative — a "temporary" adapter returning plausible Arabic text and a
0.91 confidence — is far more dangerous than an outage. In a heritage context
a fabricated reading can be screenshotted, cited, and propagated; it is
indistinguishable from a real result to every consumer. Silence is recoverable,
invented history is not. See ADR-0004.

Each adapter is replaced by a real one at the composition root as models land;
no code outside this module and the container changes.
"""

from __future__ import annotations

from dataclasses import dataclass

from qalam.domain.entities import (
    DetectedRegion,
    ImageReference,
    OcrOutput,
    TranslationOutput,
)
from qalam.domain.value_objects import Confidence, Evidence, Script


@dataclass(frozen=True, slots=True)
class _Unavailable:
    """Shared availability reporting for not-yet-implemented capabilities."""

    capability: str
    reason: str
    tracking: str
    """Milestone or issue where this capability is scheduled. Keeps the gap visible."""

    @property
    def id(self) -> str:
        return f"unavailable:{self.capability}"

    @property
    def is_available(self) -> bool:
        return False

    @property
    def availability_reason(self) -> str:
        return f"{self.reason} (scheduled: {self.tracking})"


@dataclass(frozen=True, slots=True)
class UnavailablePreprocessor(_Unavailable):
    capability: str = "image_preprocessing"
    reason: str = "No image enhancement or perspective-correction pipeline is configured."
    tracking: str = "M2"

    async def preprocess(self, image: ImageReference) -> ImageReference:
        raise NotImplementedError(self.availability_reason)


@dataclass(frozen=True, slots=True)
class UnavailableDetector(_Unavailable):
    capability: str = "inscription_detection"
    reason: str = "No inscription detection model weights are configured."
    tracking: str = "M2"

    async def detect(self, image: ImageReference) -> tuple[DetectedRegion, ...]:
        raise NotImplementedError(self.availability_reason)


@dataclass(frozen=True, slots=True)
class UnavailableScriptClassifier(_Unavailable):
    capability: str = "script_classification"
    reason: str = "No script classification model is configured."
    tracking: str = "M3"

    async def classify(
        self, image: ImageReference, region: DetectedRegion
    ) -> tuple[Script, Confidence]:
        raise NotImplementedError(self.availability_reason)


@dataclass(frozen=True, slots=True)
class UnavailableOcrEngine(_Unavailable):
    capability: str = "ocr"
    reason: str = "No OCR engine is configured; set QALAM_OCR__DEFAULT_ENGINE."
    tracking: str = "M3"

    @property
    def supported_scripts(self) -> frozenset[Script]:
        return frozenset()

    async def recognize(
        self,
        image: ImageReference,
        regions: tuple[DetectedRegion, ...],
        script: Script,
    ) -> OcrOutput:
        raise NotImplementedError(self.availability_reason)


@dataclass(frozen=True, slots=True)
class UnavailableTranslator(_Unavailable):
    capability: str = "translation"
    reason: str = "No translation engine is configured."
    tracking: str = "M4"

    async def translate(
        self, text: str, *, source_language: str, target_language: str
    ) -> TranslationOutput:
        raise NotImplementedError(self.availability_reason)


@dataclass(frozen=True, slots=True)
class UnavailableKnowledgeGraph(_Unavailable):
    capability: str = "knowledge_graph"
    reason: str = "No Heritage Knowledge Graph endpoint is configured."
    tracking: str = "M5"

    async def find_evidence(
        self, *, text: str, script: Script, civilization: str, limit: int = 10
    ) -> tuple[Evidence, ...]:
        raise NotImplementedError(self.availability_reason)
