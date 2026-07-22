"""Adapters: concrete implementations of the domain ports.

Everything that touches the outside world — model runtimes, HTTP clients,
graph drivers, file systems — lives here and nowhere else. The application
layer never imports from this package; import-linter enforces that.
"""
