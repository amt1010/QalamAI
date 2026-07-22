"""The civilization plugin contract and its registry."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from qalam.core.errors import PluginNotFoundError
from qalam.domain.value_objects import Script


@runtime_checkable
class CivilizationPlugin(Protocol):
    """Knowledge specific to one writing tradition."""

    @property
    def id(self) -> str:
        """Stable snake_case identifier, e.g. ``"islamic_epigraphy"``."""
        ...

    @property
    def display_name(self) -> str: ...

    @property
    def supported_scripts(self) -> frozenset[Script]: ...

    @property
    def default_script(self) -> Script:
        """Script assumed when classification is unavailable or ambiguous."""
        ...

    @property
    def default_target_language(self) -> str:
        """BCP-47 tag translations default to for this tradition."""
        ...

    def normalize_text(self, raw: str) -> str:
        """Canonicalize a transcription for storage and display.

        Must be *conservative*: it may remove artefacts introduced by
        recognition (stray control characters, presentation forms, padding),
        but must not discard orthographic distinctions a scholar would care
        about. Lossy folding belongs in :meth:`search_key`.
        """
        ...

    def search_key(self, text: str) -> str:
        """Aggressively fold text into a key for matching and deduplication.

        May discard real distinctions to maximize recall when comparing a
        weathered transcription against corpora. Never shown to users and never
        stored as the canonical reading.
        """
        ...


class PluginRegistry:
    """In-process registry of civilization plugins.

    Registration is explicit at the composition root rather than discovered by
    scanning. Explicit registration keeps startup deterministic, keeps the
    dependency graph readable, and prevents an unvetted package on the path
    from silently contributing heritage claims.
    """

    def __init__(self, plugins: tuple[CivilizationPlugin, ...] = ()) -> None:
        self._plugins: dict[str, CivilizationPlugin] = {}
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: CivilizationPlugin) -> None:
        """Add ``plugin``, rejecting duplicate identifiers."""
        if plugin.id in self._plugins:
            raise ValueError(
                f"A plugin with id {plugin.id!r} is already registered "
                f"({type(self._plugins[plugin.id]).__name__})"
            )
        self._plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> CivilizationPlugin:
        """Return the plugin registered as ``plugin_id``."""
        try:
            return self._plugins[plugin_id]
        except KeyError:
            raise PluginNotFoundError(plugin_id, available=self.ids()) from None

    def ids(self) -> tuple[str, ...]:
        """Registered identifiers, sorted for stable output."""
        return tuple(sorted(self._plugins))

    def all(self) -> tuple[CivilizationPlugin, ...]:
        """Every registered plugin, ordered by identifier."""
        return tuple(self._plugins[pid] for pid in self.ids())

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, plugin_id: object) -> bool:
        return plugin_id in self._plugins
