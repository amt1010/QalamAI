"""Domain entities for the inscription-analysis flow.

The shapes here are the platform's internal vocabulary. They are deliberately
*not* the HTTP contract — ``qalam.api`` owns that and maps across the boundary,
so wire compatibility and internal refactoring stay independent (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

from qalam.domain.value_objects import BoundingBox, Confidence, Evidence, Script


class AnalysisMode(StrEnum):
    """Audience for the response, which governs depth and presentation.

    The mode never changes what the platform *believes* — only how much of its
    reasoning and evidence it surfaces.
    """

    TOURIST = "tourist"
    """Plain-language narrative; evidence summarized rather than enumerated."""

    RESEARCH = "research"
    """Full evidence chains, alternative readings, and confidence breakdowns."""

    DEVELOPER = "developer"
    """Everything in research mode plus per-stage diagnostics and timings."""


class StageStatus(StrEnum):
    """Outcome of a single pipeline stage."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    """No implementation is configured. Expected during early milestones."""
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ImageReference:
    """A pointer to the image under analysis.

    The platform passes references rather than bytes through the domain so that
    large payloads stay in one place and stages can be distributed later
    without reshaping the interfaces.
    """

    uri: str
    content_type: str | None = None
    sha256: str | None = None
    """Content hash, used for caching, deduplication, and reproducibility."""

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise ValueError("ImageReference.uri must not be empty")


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    """An instruction to analyze one image."""

    image: ImageReference
    mode: AnalysisMode = AnalysisMode.TOURIST
    civilization: str | None = None
    """Plugin identifier. ``None`` means use the configured default."""
    script_hint: Script | None = None
    """Caller's hint about the script, used to shortcut classification."""
    request_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class DetectedRegion:
    """A candidate inscription region located within the image."""

    box: BoundingBox
    confidence: Confidence
    label: str = "inscription"


@dataclass(frozen=True, slots=True)
class RecognizedLine:
    """A single line of text read from a region."""

    text: str
    confidence: Confidence
    script: Script = Script.UNKNOWN
    box: BoundingBox | None = None


@dataclass(frozen=True, slots=True)
class OcrOutput:
    """Result of running an OCR engine over one or more regions."""

    lines: tuple[RecognizedLine, ...]
    engine_id: str

    @property
    def text(self) -> str:
        """The recognized lines joined in reading order."""
        return "\n".join(line.text for line in self.lines)

    @property
    def mean_confidence(self) -> Confidence:
        """Length-weighted mean confidence across lines.

        Weighting by character count keeps a confidently-read long line from
        being dragged down by a short uncertain fragment.
        """
        if not self.lines:
            return Confidence(0.0)
        weights = [max(len(line.text), 1) for line in self.lines]
        total = sum(weights)
        weighted = sum(
            w * line.confidence.value for w, line in zip(weights, self.lines, strict=True)
        )
        return Confidence(weighted / total)


@dataclass(frozen=True, slots=True)
class TranslationOutput:
    """A translation of recognized text into a target language."""

    text: str
    source_language: str
    target_language: str
    engine_id: str
    confidence: Confidence


@dataclass(frozen=True, slots=True)
class HeritageClaim:
    """A historical or interpretive statement, with its supporting evidence.

    Construction fails without evidence. This is the structural guarantee
    behind "the LLM must never hallucinate historical facts": there is no
    representation of an unsupported claim for a generator to produce.
    """

    statement: str
    evidence: tuple[Evidence, ...]
    subject_uri: str | None = None
    """HKG node this claim is about, when it originates from the graph."""

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise ValueError("HeritageClaim.statement must not be empty")
        if not self.evidence:
            raise ValueError(
                f"HeritageClaim requires at least one Evidence; "
                f"unsupported statement rejected: {self.statement!r}"
            )

    @property
    def confidence(self) -> Confidence:
        """Confidence of the strongest piece of supporting evidence."""
        return max((e.confidence for e in self.evidence), key=lambda c: c.value)


@dataclass(frozen=True, slots=True)
class StageReport:
    """Diagnostics for one pipeline stage, surfaced in developer mode."""

    name: str
    status: StageStatus
    duration_ms: float
    detail: str | None = None
    implementation_id: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Everything the platform concluded about one image.

    Every field is optional-by-absence rather than filled with defaults: a
    stage that did not run contributes nothing, and ``stages`` records why.
    """

    request_id: UUID
    civilization: str
    regions: tuple[DetectedRegion, ...] = ()
    ocr: OcrOutput | None = None
    translation: TranslationOutput | None = None
    claims: tuple[HeritageClaim, ...] = ()
    stages: tuple[StageReport, ...] = ()

    @property
    def is_complete(self) -> bool:
        """Whether every stage that ran reached a successful conclusion."""
        return all(s.status is StageStatus.COMPLETED for s in self.stages)

    @property
    def unavailable_capabilities(self) -> tuple[str, ...]:
        """Names of stages that had no configured implementation."""
        return tuple(s.name for s in self.stages if s.status is StageStatus.UNAVAILABLE)
