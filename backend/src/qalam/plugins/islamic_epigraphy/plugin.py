"""The Islamic epigraphy civilization plugin."""

from __future__ import annotations

from dataclasses import dataclass

from qalam.domain.value_objects import Script
from qalam.plugins.islamic_epigraphy import arabic


@dataclass(frozen=True, slots=True)
class IslamicEpigraphyPlugin:
    """Arabic-script monumental inscription knowledge.

    Covers Arabic alongside Persian and Ottoman Turkish, which share the script
    and much of the monumental repertoire. Should those traditions later need
    materially different handling — distinct corpora, distinct orthographic
    rules — they split into their own plugins; that is a plugin-level change
    with no effect on the platform core.
    """

    target_language: str = "en"

    @property
    def id(self) -> str:
        return "islamic_epigraphy"

    @property
    def display_name(self) -> str:
        return "Islamic Epigraphy"

    @property
    def supported_scripts(self) -> frozenset[Script]:
        return frozenset({Script.ARABIC, Script.PERSIAN, Script.OTTOMAN_TURKISH})

    @property
    def default_script(self) -> Script:
        return Script.ARABIC

    @property
    def default_target_language(self) -> str:
        return self.target_language

    def normalize_text(self, raw: str) -> str:
        """Canonicalize a transcription, preserving vocalization."""
        return arabic.canonicalize(raw)

    def search_key(self, text: str) -> str:
        """Fold a transcription into a lossy corpus-matching key."""
        return arabic.fold(text)
