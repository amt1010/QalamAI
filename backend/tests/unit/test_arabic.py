"""Arabic normalization behaviour.

These tests pin the distinction the platform depends on: canonicalization must
preserve scholarly detail, folding may destroy it.
"""

from __future__ import annotations

import pytest

from qalam.plugins.islamic_epigraphy import arabic

pytestmark = pytest.mark.unit


class TestCanonicalize:
    def test_removes_kashida_elongation(self) -> None:
        assert arabic.canonicalize("الرحـــمن") == "الرحمن"

    def test_preserves_diacritics(self) -> None:
        vocalized = "بِسْمِ"
        assert arabic.canonicalize(vocalized) == vocalized
        assert arabic.has_diacritics(arabic.canonicalize(vocalized))

    def test_expands_allah_ligature(self) -> None:
        """U+FDF2 is a presentation-form ligature OCR engines frequently emit."""
        assert arabic.canonicalize("ﷲ") == "الله"

    def test_strips_zero_width_and_bidi_marks(self) -> None:
        assert arabic.canonicalize("ا​ل‏له") == "الله"

    def test_collapses_whitespace(self) -> None:
        assert arabic.canonicalize("  بسم   الله \n الرحمن ") == "بسم الله الرحمن"

    def test_is_idempotent(self) -> None:
        once = arabic.canonicalize("بِسْمِ ٱللَّهِ الرحـــمن")
        assert arabic.canonicalize(once) == once


class TestFold:
    def test_removes_diacritics(self) -> None:
        assert arabic.fold("بِسْمِ") == arabic.fold("بسم")

    def test_unifies_alef_variants(self) -> None:
        keys = {arabic.fold(form) for form in ("أحمد", "احمد", "إحمد", "آحمد")}
        assert len(keys) == 1

    def test_folds_alef_wasla(self) -> None:
        assert arabic.fold("ٱللَّه") == arabic.fold("الله")

    def test_folds_ta_marbuta_to_ha(self) -> None:
        assert arabic.fold("مدينة") == arabic.fold("مدينه")

    def test_folds_hamza_seats(self) -> None:
        assert arabic.fold("مسؤول") == arabic.fold("مسوول")
        assert arabic.fold("قائم") == arabic.fold("قايم")

    def test_normalizes_arabic_indic_digits(self) -> None:
        assert "1370" in arabic.fold("١٣٧٠")

    def test_drops_punctuation(self) -> None:
        assert arabic.fold("بسم، الله!") == "بسم الله"

    def test_is_idempotent(self) -> None:
        once = arabic.fold("بِسْمِ ٱللَّهِ الرحـــمن")
        assert arabic.fold(once) == once

    def test_distinct_words_do_not_collide(self) -> None:
        """Folding is lossy, but must not erase genuine lexical difference."""
        assert arabic.fold("كتاب") != arabic.fold("كاتب")


class TestStripDiacritics:
    def test_removes_vocalization_but_keeps_letters(self) -> None:
        assert arabic.strip_diacritics("بِسْمِ") == "بسم"

    def test_reports_presence_of_diacritics(self) -> None:
        assert arabic.has_diacritics("بِسْمِ")
        assert not arabic.has_diacritics("بسم")

    def test_produces_training_pair_side(self) -> None:
        """Undiacritized side of a diacritic-restoration training pair."""
        vocalized = "بِسْمِ ٱللَّهِ"
        bare = arabic.strip_diacritics(vocalized)
        assert not arabic.has_diacritics(bare)
        assert len(bare) < len(vocalized)
