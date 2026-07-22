"""Application layer: use cases that orchestrate ports and plugins.

Sits *below* ``adapters`` in the layering contract. That ordering is the point:
import-linter will reject any attempt by an orchestrator to import a concrete
engine, so "replaceable AI components" is enforced by CI rather than by
reviewer vigilance.
"""

from qalam.application.pipeline import AnalysisPipeline, PipelineComponents

__all__ = ["AnalysisPipeline", "PipelineComponents"]
