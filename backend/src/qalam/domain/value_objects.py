"""Immutable domain value objects.

Value objects are frozen and self-validating: an instance that exists is an
instance that is valid. This pushes error handling to construction time rather
than scattering defensive checks through the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Script(StrEnum):
    """Writing systems the platform can reason about.

    Extending this enum is how a new civilization plugin declares the scripts
    it handles. The platform core never branches on these values; only plugins
    and adapters do.
    """

    ARABIC = "arabic"
    PERSIAN = "persian"
    OTTOMAN_TURKISH = "ottoman_turkish"
    BRAHMI = "brahmi"
    DEVANAGARI = "devanagari"
    TAMIL = "tamil"
    HEBREW = "hebrew"
    GREEK = "greek"
    LATIN = "latin"
    EGYPTIAN_HIEROGLYPHS = "egyptian_hieroglyphs"
    CUNEIFORM = "cuneiform"
    UNKNOWN = "unknown"


class EvidenceKind(StrEnum):
    """Where a claim's support comes from, ordered loosely by strength."""

    ACADEMIC_PUBLICATION = "academic_publication"
    PRIMARY_SOURCE = "primary_source"
    MUSEUM_RECORD = "museum_record"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    MODEL_INFERENCE = "model_inference"


@dataclass(frozen=True, slots=True)
class Confidence:
    """A calibrated probability in [0, 1].

    Wrapped in a type rather than passed as a bare float so that confidences
    cannot be silently confused with scores, distances, or percentages.
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be within [0, 1], got {self.value}")

    def __float__(self) -> float:
        return self.value

    def meets(self, threshold: float) -> bool:
        """Return whether this confidence is at least ``threshold``."""
        return self.value >= threshold

    @classmethod
    def certain(cls) -> Confidence:
        return cls(1.0)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned region in pixel coordinates, origin at the top-left."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"BoundingBox must have positive extent, got {self.width}x{self.height}"
            )
        if self.x < 0 or self.y < 0:
            raise ValueError(f"BoundingBox origin must be non-negative, got ({self.x}, {self.y})")

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class Citation:
    """A pointer to a source that a human can independently verify."""

    title: str
    identifier: str
    """Stable identifier: DOI, ISBN, museum accession number, or HKG node URI."""
    kind: EvidenceKind
    locator: str | None = None
    """Page, folio, plate, or fragment reference within the source."""
    url: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Citation.title must not be empty")
        if not self.identifier.strip():
            raise ValueError("Citation.identifier must not be empty")


@dataclass(frozen=True, slots=True)
class Evidence:
    """Support for a single claim, with provenance and confidence.

    Provenance, confidence, and citation are mandatory across the platform —
    see ADR-0005. An assertion the platform cannot attribute is an assertion it
    does not make.
    """

    citation: Citation
    confidence: Confidence
    note: str | None = None
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def kind(self) -> EvidenceKind:
        return self.citation.kind
