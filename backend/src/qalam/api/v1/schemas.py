"""Wire schemas for API v1, and the mapping from domain entities.

These types are the public contract. They are intentionally separate from
``qalam.domain.entities``: the domain is free to be refactored, split, or
re-modelled without breaking a deployed mobile app, and the contract is free to
stay stable for years. The cost is an explicit mapping function, which is also
the place where audience-dependent redaction happens. See ADR-0003.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from qalam.domain.entities import (
    AnalysisMode,
    AnalysisResult,
    DetectedRegion,
    HeritageClaim,
    OcrOutput,
    RecognizedLine,
    StageReport,
    TranslationOutput,
)
from qalam.domain.value_objects import BoundingBox, Evidence, Script

# --- Requests ---------------------------------------------------------------


class AnalyzeRequestSchema(BaseModel):
    """Request to analyze a single inscription image."""

    model_config = ConfigDict(extra="forbid")

    image_url: Annotated[str, Field(min_length=1, max_length=2048)]
    mode: AnalysisMode = AnalysisMode.TOURIST
    civilization: str | None = Field(
        default=None,
        description="Civilization plugin id. Omit to use the server default.",
    )
    script_hint: Script | None = Field(
        default=None,
        description="Skip script classification when the caller already knows the script.",
    )
    content_type: str | None = None
    sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description="Lowercase hex SHA-256 of the image, for caching and reproducibility.",
    )


# --- Responses --------------------------------------------------------------


class BoundingBoxSchema(BaseModel):
    x: int
    y: int
    width: int
    height: int


class RegionSchema(BaseModel):
    box: BoundingBoxSchema
    confidence: float
    label: str


class LineSchema(BaseModel):
    text: str
    confidence: float
    script: Script
    box: BoundingBoxSchema | None = None


class OcrSchema(BaseModel):
    text: str
    lines: list[LineSchema]
    engine_id: str
    mean_confidence: float


class TranslationSchema(BaseModel):
    text: str
    source_language: str
    target_language: str
    engine_id: str
    confidence: float


class CitationSchema(BaseModel):
    title: str
    identifier: str
    kind: str
    locator: str | None = None
    url: str | None = None


class EvidenceSchema(BaseModel):
    citation: CitationSchema
    confidence: float
    note: str | None = None


class ClaimSchema(BaseModel):
    """A historical statement. ``evidence`` is never empty — see ADR-0005."""

    statement: str
    confidence: float
    subject_uri: str | None = None
    evidence: list[EvidenceSchema] = Field(min_length=1)


class StageSchema(BaseModel):
    name: str
    status: str
    duration_ms: float
    detail: str | None = None
    implementation_id: str | None = None


class AnalyzeResponseSchema(BaseModel):
    """Result of an analysis.

    Absent fields mean the corresponding stage produced nothing; they are never
    filled with defaults. ``unavailable_capabilities`` names what the
    deployment could not do, so a client can degrade its UI deliberately rather
    than guess.
    """

    request_id: UUID
    civilization: str
    complete: bool
    unavailable_capabilities: list[str] = Field(default_factory=list)
    regions: list[RegionSchema] = Field(default_factory=list)
    ocr: OcrSchema | None = None
    translation: TranslationSchema | None = None
    claims: list[ClaimSchema] = Field(default_factory=list)
    stages: list[StageSchema] | None = Field(
        default=None,
        description="Per-stage diagnostics. Present in developer mode only.",
    )


class CivilizationSchema(BaseModel):
    id: str
    display_name: str
    supported_scripts: list[Script]
    default_script: Script
    default_target_language: str


class CapabilityStatusSchema(BaseModel):
    name: str
    available: bool
    implementation_id: str
    reason: str


class ReadinessSchema(BaseModel):
    """Which capabilities this deployment can currently serve.

    Distinct from liveness: the process can be perfectly healthy while unable
    to read an inscription. Operators need to see that difference.
    """

    ready: bool
    environment: str
    version: str
    capabilities: list[CapabilityStatusSchema]


class ErrorSchema(BaseModel):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


# --- Mapping ----------------------------------------------------------------


def _box(box: BoundingBox) -> BoundingBoxSchema:
    return BoundingBoxSchema(x=box.x, y=box.y, width=box.width, height=box.height)


def _region(region: DetectedRegion) -> RegionSchema:
    return RegionSchema(
        box=_box(region.box), confidence=region.confidence.value, label=region.label
    )


def _line(line: RecognizedLine) -> LineSchema:
    return LineSchema(
        text=line.text,
        confidence=line.confidence.value,
        script=line.script,
        box=_box(line.box) if line.box is not None else None,
    )


def _ocr(ocr: OcrOutput) -> OcrSchema:
    return OcrSchema(
        text=ocr.text,
        lines=[_line(line) for line in ocr.lines],
        engine_id=ocr.engine_id,
        mean_confidence=ocr.mean_confidence.value,
    )


def _translation(translation: TranslationOutput) -> TranslationSchema:
    return TranslationSchema(
        text=translation.text,
        source_language=translation.source_language,
        target_language=translation.target_language,
        engine_id=translation.engine_id,
        confidence=translation.confidence.value,
    )


def _evidence(evidence: Evidence) -> EvidenceSchema:
    return EvidenceSchema(
        citation=CitationSchema(
            title=evidence.citation.title,
            identifier=evidence.citation.identifier,
            kind=evidence.citation.kind.value,
            locator=evidence.citation.locator,
            url=evidence.citation.url,
        ),
        confidence=evidence.confidence.value,
        note=evidence.note,
    )


def _claim(claim: HeritageClaim) -> ClaimSchema:
    return ClaimSchema(
        statement=claim.statement,
        confidence=claim.confidence.value,
        subject_uri=claim.subject_uri,
        evidence=[_evidence(item) for item in claim.evidence],
    )


def _stage(stage: StageReport) -> StageSchema:
    return StageSchema(
        name=stage.name,
        status=stage.status.value,
        duration_ms=round(stage.duration_ms, 3),
        detail=stage.detail,
        implementation_id=stage.implementation_id,
    )


def to_response(result: AnalysisResult, mode: AnalysisMode) -> AnalyzeResponseSchema:
    """Map a domain result onto the wire contract for the requested audience.

    Mode governs disclosure, never substance: the platform's conclusions are
    identical across modes, and only the depth of diagnostics differs.
    """
    return AnalyzeResponseSchema(
        request_id=result.request_id,
        civilization=result.civilization,
        complete=result.is_complete,
        unavailable_capabilities=list(result.unavailable_capabilities),
        regions=[_region(region) for region in result.regions],
        ocr=_ocr(result.ocr) if result.ocr is not None else None,
        translation=_translation(result.translation) if result.translation is not None else None,
        claims=[_claim(claim) for claim in result.claims],
        stages=(
            [_stage(stage) for stage in result.stages] if mode is AnalysisMode.DEVELOPER else None
        ),
    )
