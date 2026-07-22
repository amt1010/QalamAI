"""Arabic orthographic normalization for epigraphic transcriptions.

Two distinct operations, deliberately kept apart:

``canonicalize``
    Removes only what recognition artefacts introduce — presentation forms,
    kashida elongation, zero-width marks, irregular whitespace. **Diacritics
    are preserved.** Vocalization carries meaning in Quranic and monumental
    text, and diacritic restoration is itself a planned platform capability;
    a canonical form that discards harakat would destroy its own ground truth.

``fold``
    Aggressively collapses orthographic variation to maximize recall when
    matching a weathered reading against a corpus. Lossy by design. Used as a
    lookup key only — never displayed, never stored as the reading.

References for the folding rules are recorded in RESEARCH_LOG.md.
"""

from __future__ import annotations

import re
import unicodedata

# --- Codepoints -------------------------------------------------------------

TATWEEL = "ـ"
"""Kashida / elongation. Purely a calligraphic stretch, never phonemic."""

ZERO_WIDTH = "​‌‍‎‏﻿"
"""Zero-width and bidi control characters that survive copy/paste and OCR."""

_HARAKAT = (
    "ً-ْ"  # tanwin, fatha, damma, kasra, shadda, sukun
    "ٓ-ٕ"  # maddah and hamza above/below
    "ٖ-ٟ"  # extended Quranic vowel marks
    "ٰ"  # superscript (dagger) alef
)
_QURANIC_MARKS = "ۖ-ۭ"
"""Recitation, sajdah, and verse-annotation signs used in Quranic orthography."""

_DIACRITICS_RE = re.compile(f"[{_HARAKAT}{_QURANIC_MARKS}]")
_TATWEEL_RE = re.compile(TATWEEL)
_ZERO_WIDTH_RE = re.compile(f"[{ZERO_WIDTH}]")
_WHITESPACE_RE = re.compile(r"\s+")

# Characters kept by ``fold``: Arabic letters, ASCII alphanumerics, and space.
_FOLD_KEEP_RE = re.compile(r"[^ء-ي٠-٩a-z0-9 ]")

_ALEF_VARIANTS = str.maketrans(
    {
        "آ": "ا",  # آ  alef with madda
        "أ": "ا",  # أ  alef with hamza above
        "إ": "ا",  # إ  alef with hamza below
        "ٱ": "ا",  # ٱ  alef wasla
        "ٲ": "ا",  # ٲ  alef with wavy hamza above
        "ٳ": "ا",  # ٳ  alef with wavy hamza below
        "ٵ": "ا",  # ٵ  high hamza alef
    }
)

_SEAT_VARIANTS = str.maketrans(
    {
        "ى": "ي",  # ى  alef maqsura   -> ya
        "ة": "ه",  # ة  ta marbuta     -> ha
        "ؤ": "و",  # ؤ  hamza on waw   -> waw
        "ئ": "ي",  # ئ  hamza on ya    -> ya
        "ء": "",  # ء  standalone hamza dropped entirely
    }
)

_ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def canonicalize(raw: str) -> str:
    """Return the scholarly canonical form of ``raw``.

    Applies NFKC (which resolves Arabic Presentation Forms A/B that OCR engines
    frequently emit, and expands ligatures such as U+FDF2 ``ﷲ`` to ``الله``),
    then strips artefacts. Diacritics survive.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _TATWEEL_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def fold(text: str) -> str:
    """Return a lossy matching key for ``text``.

    Beyond :func:`canonicalize`, this removes all vocalization, unifies alef
    and hamza-seat variants, folds ta marbuta to ha, converts Arabic-Indic
    digits, and discards punctuation. Two readings that fold to the same key
    are candidates for being the same inscription — not proof of it.
    """
    result = canonicalize(text).lower()
    result = _DIACRITICS_RE.sub("", result)
    result = result.translate(_ALEF_VARIANTS)
    result = result.translate(_SEAT_VARIANTS)
    result = result.translate(_ARABIC_INDIC_DIGITS)
    result = _FOLD_KEEP_RE.sub(" ", result)
    return _WHITESPACE_RE.sub(" ", result).strip()


def strip_diacritics(text: str) -> str:
    """Remove vocalization marks while preserving letter identity.

    Exposed separately because diacritic *restoration* models need matched
    (undiacritized, diacritized) pairs, and this is how the undiacritized side
    of a training pair is produced.
    """
    return _DIACRITICS_RE.sub("", text)


def has_diacritics(text: str) -> bool:
    """Whether ``text`` carries any vocalization marks."""
    return _DIACRITICS_RE.search(text) is not None
