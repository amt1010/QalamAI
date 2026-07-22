"""Value object invariants — including the platform's anti-hallucination rule."""

from __future__ import annotations

import pytest

from qalam.domain.entities import HeritageClaim, OcrOutput, RecognizedLine
from qalam.domain.value_objects import (
    BoundingBox,
    Citation,
    Confidence,
    Evidence,
    EvidenceKind,
    Script,
)

pytestmark = pytest.mark.unit


def _evidence(confidence: float = 0.9, note: str | None = None) -> Evidence:
    return Evidence(
        citation=Citation(
            title="Corpus Inscriptionum Arabicarum",
            identifier="doi:10.0000/example",
            kind=EvidenceKind.ACADEMIC_PUBLICATION,
        ),
        confidence=Confidence(confidence),
        note=note,
    )


class TestConfidence:
    @pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
    def test_accepts_unit_interval(self, value: float) -> None:
        assert float(Confidence(value)) == value

    @pytest.mark.parametrize("value", [-0.01, 1.01, 42.0])
    def test_rejects_values_outside_unit_interval(self, value: float) -> None:
        with pytest.raises(ValueError, match=r"within \[0, 1\]"):
            Confidence(value)

    def test_meets_threshold(self) -> None:
        assert Confidence(0.8).meets(0.8)
        assert not Confidence(0.79).meets(0.8)


class TestBoundingBox:
    def test_rejects_non_positive_extent(self) -> None:
        with pytest.raises(ValueError, match="positive extent"):
            BoundingBox(x=0, y=0, width=0, height=10)

    def test_rejects_negative_origin(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            BoundingBox(x=-1, y=0, width=10, height=10)

    def test_area(self) -> None:
        assert BoundingBox(x=0, y=0, width=4, height=5).area == 20


class TestCitation:
    def test_requires_title_and_identifier(self) -> None:
        with pytest.raises(ValueError, match="title"):
            Citation(title="  ", identifier="x", kind=EvidenceKind.MUSEUM_RECORD)
        with pytest.raises(ValueError, match="identifier"):
            Citation(title="x", identifier="", kind=EvidenceKind.MUSEUM_RECORD)


class TestHeritageClaim:
    def test_rejects_a_claim_with_no_evidence(self) -> None:
        """The structural guarantee against hallucinated history (ADR-0005).

        There must be no way to represent an unsupported historical claim, so
        that no generator can emit one.
        """
        with pytest.raises(ValueError, match="requires at least one Evidence"):
            HeritageClaim(statement="Built by Shah Jahan in 1632.", evidence=())

    def test_rejects_empty_statement(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            HeritageClaim(statement="   ", evidence=(_evidence(),))

    def test_confidence_is_that_of_strongest_evidence(self) -> None:
        claim = HeritageClaim(
            statement="Commissioned under the Mughal dynasty.",
            evidence=(_evidence(0.6), _evidence(0.91), _evidence(0.4)),
        )
        assert claim.confidence.value == pytest.approx(0.91)


class TestOcrOutput:
    def test_text_joins_lines_in_order(self) -> None:
        output = OcrOutput(
            lines=(
                RecognizedLine(text="بسم", confidence=Confidence(0.9), script=Script.ARABIC),
                RecognizedLine(text="الله", confidence=Confidence(0.9), script=Script.ARABIC),
            ),
            engine_id="test",
        )
        assert output.text == "بسم\nالله"

    def test_mean_confidence_is_length_weighted(self) -> None:
        """A long confident line should not be dragged down by a short unsure one."""
        output = OcrOutput(
            lines=(
                RecognizedLine(text="a" * 100, confidence=Confidence(0.9)),
                RecognizedLine(text="b", confidence=Confidence(0.1)),
            ),
            engine_id="test",
        )
        assert output.mean_confidence.value == pytest.approx((100 * 0.9 + 1 * 0.1) / 101)

    def test_mean_confidence_of_empty_output_is_zero(self) -> None:
        assert OcrOutput(lines=(), engine_id="test").mean_confidence.value == 0.0
