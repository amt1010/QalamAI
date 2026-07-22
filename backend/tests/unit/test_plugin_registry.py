"""Plugin registry behaviour and the Islamic epigraphy plugin's contract."""

from __future__ import annotations

import pytest

from qalam.core.errors import PluginNotFoundError
from qalam.domain.value_objects import Script
from qalam.plugins.base import CivilizationPlugin, PluginRegistry
from qalam.plugins.islamic_epigraphy import IslamicEpigraphyPlugin

pytestmark = pytest.mark.unit


class TestPluginRegistry:
    def test_registers_and_retrieves(self) -> None:
        plugin = IslamicEpigraphyPlugin()
        registry = PluginRegistry((plugin,))
        assert registry.get("islamic_epigraphy") is plugin
        assert "islamic_epigraphy" in registry
        assert len(registry) == 1

    def test_rejects_duplicate_ids(self) -> None:
        registry = PluginRegistry((IslamicEpigraphyPlugin(),))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(IslamicEpigraphyPlugin())

    def test_unknown_id_raises_with_available_options(self) -> None:
        registry = PluginRegistry((IslamicEpigraphyPlugin(),))
        with pytest.raises(PluginNotFoundError) as excinfo:
            registry.get("cuneiform")
        assert excinfo.value.details["available"] == ["islamic_epigraphy"]
        assert excinfo.value.http_status == 404

    def test_ids_are_sorted_for_stable_output(self) -> None:
        registry = PluginRegistry((IslamicEpigraphyPlugin(),))
        assert registry.ids() == tuple(sorted(registry.ids()))


class TestIslamicEpigraphyPlugin:
    def test_satisfies_the_plugin_protocol(self) -> None:
        assert isinstance(IslamicEpigraphyPlugin(), CivilizationPlugin)

    def test_covers_the_arabic_script_family(self) -> None:
        plugin = IslamicEpigraphyPlugin()
        assert Script.ARABIC in plugin.supported_scripts
        assert Script.PERSIAN in plugin.supported_scripts
        assert plugin.default_script is Script.ARABIC

    def test_does_not_claim_unrelated_scripts(self) -> None:
        plugin = IslamicEpigraphyPlugin()
        assert Script.BRAHMI not in plugin.supported_scripts
        assert Script.CUNEIFORM not in plugin.supported_scripts

    def test_normalize_preserves_diacritics_but_search_key_does_not(self) -> None:
        plugin = IslamicEpigraphyPlugin()
        raw = "بِسْمِ ٱللَّهِ"
        assert "ِ" in plugin.normalize_text(raw)  # kasra survives canonicalization
        assert "ِ" not in plugin.search_key(raw)  # but not folding

    def test_target_language_is_configurable(self) -> None:
        assert IslamicEpigraphyPlugin(target_language="ur").default_target_language == "ur"
