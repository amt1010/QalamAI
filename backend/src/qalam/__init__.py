"""QalamAI — Heritage Intelligence Platform.

Layering (enforced by import-linter, see ADR-0001):

    api  >  composition  >  adapters  >  plugins  >  domain  >  core

Each layer may import only from layers below it. ``domain`` additionally may
not import any web framework, so it stays reusable from training scripts,
batch jobs, and future non-HTTP entry points.
"""

__version__ = "0.1.0"
