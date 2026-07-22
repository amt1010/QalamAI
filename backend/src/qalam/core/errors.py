"""Platform error taxonomy.

Every error carries a stable machine-readable ``code``. Clients (mobile, web,
kiosk, third-party API consumers) branch on the code, never on the message —
messages are free to change without breaking compatibility.
"""

from __future__ import annotations


class QalamError(Exception):
    """Base class for every error raised deliberately by the platform."""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, object] = details or {}

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "details": self.details}


class ConfigurationError(QalamError):
    """The platform is misconfigured and cannot serve requests correctly."""

    code = "configuration_error"
    http_status = 500


class ValidationError(QalamError):
    """Caller supplied input the platform cannot act on."""

    code = "validation_error"
    http_status = 422


class CapabilityUnavailableError(QalamError):
    """A required pipeline capability has no usable implementation.

    Raised when, for example, no OCR engine is registered for the requested
    script. This is a first-class, expected condition during early milestones:
    the platform declares the gap honestly rather than returning fabricated
    output. See ADR-0004.
    """

    code = "capability_unavailable"
    http_status = 503

    def __init__(self, capability: str, *, reason: str) -> None:
        super().__init__(
            f"Capability {capability!r} is not available: {reason}",
            details={"capability": capability, "reason": reason},
        )
        self.capability = capability
        self.reason = reason


class PluginNotFoundError(QalamError):
    """No civilization plugin is registered under the requested identifier."""

    code = "plugin_not_found"
    http_status = 404

    def __init__(self, plugin_id: str, *, available: tuple[str, ...]) -> None:
        super().__init__(
            f"No civilization plugin registered as {plugin_id!r}",
            details={"requested": plugin_id, "available": list(available)},
        )
        self.plugin_id = plugin_id


class UnsupportedInputError(QalamError):
    """The input is well-formed but outside what the platform currently handles."""

    code = "unsupported_input"
    http_status = 415
