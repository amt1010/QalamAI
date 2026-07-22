"""Typed application configuration.

Configuration over hardcoding: every tunable is declared here with a type, a
default, and documentation. Values are sourced from environment variables
(prefix ``QALAM_``) and an optional ``.env`` file. Nested settings use a
double-underscore delimiter, e.g. ``QALAM_OCR__DEFAULT_ENGINE=tesseract``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
LogFormat = Literal["console", "json"]


class OcrSettings(BaseSettings):
    """Settings for the OCR subsystem."""

    default_engine: str = Field(
        default="unavailable",
        description=(
            "Identifier of the OCR adapter to use when a request does not "
            "specify one. Defaults to the explicitly-unavailable adapter so "
            "that an unconfigured deployment fails loudly instead of "
            "returning fabricated text."
        ),
    )
    min_confidence: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Recognitions below this confidence are dropped from results.",
    )


class KnowledgeGraphSettings(BaseSettings):
    """Settings for the Heritage Knowledge Graph client."""

    endpoint: str | None = Field(
        default=None,
        description="Base URL of the HKG service. None disables HKG-backed answers.",
    )
    timeout_seconds: float = Field(default=5.0, gt=0.0)
    require_evidence: bool = Field(
        default=True,
        description=(
            "When true, any historical claim returned to a client must carry at "
            "least one supporting citation. This is the platform's structural "
            "defence against hallucinated history and must stay true in "
            "production. See ADR-0005."
        ),
    )


class Settings(BaseSettings):
    """Root configuration object."""

    model_config = SettingsConfigDict(
        env_prefix="QALAM_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    environment: Environment = Field(default="local")
    debug: bool = Field(default=False)

    api_title: str = Field(default="QalamAI")
    api_version: str = Field(default="0.1.0")
    api_prefix: str = Field(default="/api/v1")

    log_level: str = Field(default="INFO")
    log_format: LogFormat = Field(
        default="console",
        description="'console' for human-readable local output, 'json' for aggregators.",
    )

    default_civilization: str = Field(
        default="islamic_epigraphy",
        description="Civilization plugin used when a request does not name one.",
    )

    ocr: OcrSettings = Field(default_factory=OcrSettings)
    knowledge_graph: KnowledgeGraphSettings = Field(default_factory=KnowledgeGraphSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so that configuration is read once per process. Tests that need
    different values should call ``get_settings.cache_clear()`` or construct a
    ``Settings`` instance directly and inject it.
    """
    return Settings()
