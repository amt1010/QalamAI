"""Composition root: the one place where interfaces meet implementations.

Dependency injection here is explicit construction, not a DI framework. With a
dependency graph this size, a container library would add indirection, magic,
and a runtime dependency while removing the single readable file that answers
"what is actually wired up in production?". Revisit if the graph outgrows it.
See ADR-0007.
"""

from qalam.composition.container import Container, build_container

__all__ = ["Container", "build_container"]
