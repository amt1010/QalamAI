"""Ports: the interfaces every AI component must satisfy.

"Replaceable AI components" is only real if the platform depends on interfaces
rather than implementations. Everything the pipeline needs is declared here as
a ``Protocol``; concrete engines live in ``qalam.adapters`` and are bound at
the composition root.

Ports are ``async`` because the majority of stages are I/O-bound (HKG queries,
hosted translation, remote inference). CPU-bound adapters — local CV and OCR
models — should wrap their synchronous work in ``asyncio.to_thread`` rather
than blocking the event loop. See ADR-0006.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from qalam.domain.entities import (
    AnalysisMode,
    AnalysisResult,
    DetectedRegion,
    ImageReference,
    OcrOutput,
    TranslationOutput,
)
from qalam.domain.value_objects import Confidence, Evidence, Script


@runtime_checkable
class Capability(Protocol):
    """Common surface for every replaceable component.

    ``availability_reason`` exists so an unconfigured deployment can explain
    itself precisely ("no model weights at MODEL_DIR") instead of failing with
    a generic error.
    """

    @property
    def id(self) -> str:
        """Stable identifier, e.g. ``"tesseract-5"``. Recorded in results and logs."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether this component can currently serve requests."""
        ...

    @property
    def availability_reason(self) -> str:
        """Human-readable explanation of the current availability state."""
        ...


@runtime_checkable
class ImagePreprocessor(Capability, Protocol):
    """Enhancement, restoration, denoising, and perspective correction."""

    async def preprocess(self, image: ImageReference) -> ImageReference:
        """Return a reference to an enhanced derivative of ``image``."""
        ...


@runtime_checkable
class InscriptionDetector(Capability, Protocol):
    """Localizes inscription regions within a monument photograph."""

    async def detect(self, image: ImageReference) -> tuple[DetectedRegion, ...]:
        """Return candidate regions, ordered by descending confidence."""
        ...


@runtime_checkable
class ScriptClassifier(Capability, Protocol):
    """Identifies the writing system of a region, to route OCR."""

    async def classify(
        self, image: ImageReference, region: DetectedRegion
    ) -> tuple[Script, Confidence]: ...


@runtime_checkable
class OcrEngine(Capability, Protocol):
    """Transcribes text from located regions."""

    @property
    def supported_scripts(self) -> frozenset[Script]:
        """Scripts this engine is trained for. Used for routing, not filtering."""
        ...

    async def recognize(
        self,
        image: ImageReference,
        regions: tuple[DetectedRegion, ...],
        script: Script,
    ) -> OcrOutput: ...


@runtime_checkable
class Translator(Capability, Protocol):
    """Translates recognized text. May be offline, hosted, or hybrid."""

    async def translate(
        self, text: str, *, source_language: str, target_language: str
    ) -> TranslationOutput: ...


@runtime_checkable
class KnowledgeGraphClient(Capability, Protocol):
    """Read access to the Heritage Knowledge Graph.

    The pipeline depends on this port, never on a graph driver, so the HKG can
    be extracted into its own deployable service without touching the domain.
    """

    async def find_evidence(
        self, *, text: str, script: Script, civilization: str, limit: int = 10
    ) -> tuple[Evidence, ...]:
        """Retrieve cited evidence relevant to a transcription."""
        ...


@runtime_checkable
class Explainer(Capability, Protocol):
    """Generates natural-language interpretation from retrieved evidence.

    Implementations receive evidence and must ground every statement in it.
    An implementation that can generate without evidence violates ADR-0005.
    """

    async def explain(
        self, result: AnalysisResult, evidence: tuple[Evidence, ...], mode: AnalysisMode
    ) -> str: ...
