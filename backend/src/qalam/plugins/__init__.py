"""Civilization plugins.

A plugin contributes the knowledge that is specific to one writing tradition:
which scripts it covers, how its text is canonicalized, and how to build a
search key for matching against corpora and the Heritage Knowledge Graph.

A plugin deliberately does **not** choose or construct engines. Wiring is the
composition root's job. Keeping plugins free of infrastructure is what allows
a new civilization to be added without touching the platform core — and what
lets the layering contract place plugins below adapters.
"""

from qalam.plugins.base import CivilizationPlugin, PluginRegistry

__all__ = ["CivilizationPlugin", "PluginRegistry"]
